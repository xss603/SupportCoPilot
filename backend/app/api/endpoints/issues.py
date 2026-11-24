from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.config import settings
from app.db.session import get_db
from app.gitlab.client import gitlab_manager
from app.models.entities import (
    AuditLog,
    DuplicateCandidate,
    Issue,
    ProposedAction,
    TriageAssessment,
)
from app.schemas.common import PriorityLevel, SLACountdown, SLAStatus
from app.schemas.triage import (
    ActionExecutionResultItem,
    ApproveActionRequest,
    ApproveActionsResponse,
    ClonedTargetIssue,
    CloneIssueRequest,
    CloneIssueResponse,
    DuplicateItem,
    IssueDetailResponse,
    IssueListItem,
    IssueNoteSchema,
    ProposedActionSchema,
    RejectTriageRequest,
    RejectTriageResponse,
    ReTriageResponse,
    TriageAssessmentDetail,
)
from app.services.triage_service import triage_service

router = APIRouter(prefix="/issues", tags=["Issues & Workbench"])

_DEFAULT_SLA_MINUTES = {
    "P1": settings.SLA_P1_HOURS * 60,
    "P2": settings.SLA_P2_HOURS * 60,
    "P3": settings.SLA_P3_HOURS * 60,
    "P4": settings.SLA_P4_HOURS * 60,
}


def _build_sla_countdown(issue: Issue, priority: Optional[str]) -> Optional[SLACountdown]:
    if not issue.sla_due_at and not priority:
        return None
    prio: PriorityLevel = (priority if priority in ("P1", "P2", "P3", "P4") else "P3")  # type: ignore[assignment]
    target_minutes = _DEFAULT_SLA_MINUTES.get(prio, 1440)
    due_at = issue.sla_due_at
    if not due_at:
        return None
    now = datetime.now(timezone.utc)
    remaining = int((due_at - now).total_seconds())
    if remaining <= 0:
        sla_status: SLAStatus = "breached"
    elif remaining <= int(target_minutes * 60 * (1.0 - settings.SLA_AT_RISK_THRESHOLD_RATIO)):
        sla_status = "at_risk"
    else:
        sla_status = "ok"
    return SLACountdown(
        priority=prio,
        target_minutes=target_minutes,
        due_at=due_at,
        remaining_seconds=remaining,
        status=sla_status,
        alert_sent=bool(issue.sla_alerts) if hasattr(issue, "sla_alerts") and issue.sla_alerts else False,
    )


@router.post("/sync")
async def sync_issues_from_gitlab(
    background: BackgroundTasks,
    project_id: Optional[str] = Query(default=None, description="GitLab project ID/path; defaults to GITLAB_DEFAULT_PROJECT_ID"),
):
    """Manual pull: fetch open GitLab issues, ingest new ones and triage them in the background."""
    from app.services.sync_service import ingest_issues, triage_issues_by_id

    pid = project_id or settings.GITLAB_DEFAULT_PROJECT_ID
    if not pid:
        raise HTTPException(status_code=400, detail="No project_id given and GITLAB_DEFAULT_PROJECT_ID is not set")
    try:
        result = await ingest_issues(pid)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GitLab sync failed: {e}")
    background.add_task(triage_issues_by_id, result["new_issue_ids"])
    return {"project_id": pid, "fetched": result["fetched"], "new": result["new"], "status": "triage_queued"}


@router.get("", response_model=List[IssueListItem])
async def list_issues(
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = None,
    priority: Optional[str] = None,
    sla_status: Optional[SLAStatus] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List issues for the Triage Queue table with rich search and filtering.
    """
    stmt = (
        select(Issue)
        .options(selectinload(Issue.triage_assessments), selectinload(Issue.sla_alerts))
        .order_by(desc(Issue.created_at))
        .limit(limit)
        .offset(offset)
    )

    conditions = []
    if status_filter:
        conditions.append(Issue.status == status_filter)
    if priority:
        conditions.append(Issue.priority == priority)
    if sla_status:
        conditions.append(Issue.sla_status == sla_status)
    if search:
        conditions.append(
            or_(
                Issue.title.ilike(f"%{search}%"),
                Issue.description.ilike(f"%{search}%"),
                Issue.author_username.ilike(f"%{search}%"),
            )
        )

    if conditions:
        stmt = stmt.where(and_(*conditions))

    res = await db.execute(stmt)
    issues = res.scalars().all()

    items: List[IssueListItem] = []
    for issue in issues:
        latest_triage = issue.triage_assessments[-1] if issue.triage_assessments else None

        if category and (not latest_triage or latest_triage.category != category):
            continue
        if priority and latest_triage and latest_triage.priority != priority:
            continue

        eff_priority = (latest_triage.priority if latest_triage else None) or issue.priority
        items.append(
            IssueListItem(
                id=issue.id,
                project_id=issue.project_id,
                iid=issue.iid,
                title=issue.title,
                state=issue.state,
                author_username=issue.author_username,
                labels=issue.labels or [],
                web_url=issue.web_url,
                status=issue.status,
                category=latest_triage.category if latest_triage else None,
                priority=eff_priority,
                component=latest_triage.component if latest_triage else None,
                confidence=latest_triage.confidence if latest_triage else None,
                abstained=latest_triage.abstained if latest_triage else False,
                requires_approval=latest_triage.requires_human_approval if latest_triage else False,
                sla=_build_sla_countdown(issue, eff_priority),
                created_at=issue.created_at,
            )
        )

    return items


@router.get("/{issue_id}", response_model=IssueDetailResponse)
async def get_issue_detail(issue_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Fetches complete issue detail for the Split-Pane Workbench:
    original description, notes, SLA countdown, AI classification, citations, duplicates, and proposed actions.
    """
    stmt = (
        select(Issue)
        .where(Issue.id == issue_id)
        .options(
            selectinload(Issue.triage_assessments).selectinload(TriageAssessment.proposed_actions),
            selectinload(Issue.duplicates).selectinload(DuplicateCandidate.candidate_issue),
            selectinload(Issue.notes),
            selectinload(Issue.sla_alerts),
        )
    )
    res = await db.execute(stmt)
    issue = res.scalar_one_or_none()

    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    latest_triage = issue.triage_assessments[-1] if issue.triage_assessments else None

    triage_detail = None
    top_actions: List[ProposedActionSchema] = []
    if latest_triage:
        top_actions = [ProposedActionSchema.model_validate(a) for a in latest_triage.proposed_actions]
        triage_detail = TriageAssessmentDetail(
            id=latest_triage.id,
            category=latest_triage.category,
            priority=latest_triage.priority,
            component=latest_triage.component,
            confidence=latest_triage.confidence,
            rag_max_score=latest_triage.rag_max_score,
            abstained=latest_triage.abstained,
            redaction_applied=latest_triage.redaction_applied,
            summary=latest_triage.summary,
            root_cause_analysis=latest_triage.root_cause_analysis,
            draft_reply_markdown=latest_triage.draft_reply_markdown,
            suggested_labels=latest_triage.suggested_labels or [],
            cited_docs=latest_triage.cited_docs or [],
            diagnostic_runbook=latest_triage.diagnostic_runbook,
            latency_ms=latest_triage.latency_ms,
            requires_human_approval=latest_triage.requires_human_approval,
            approval_status=latest_triage.approval_status,
            approved_by=latest_triage.approved_by,
            approved_at=latest_triage.approved_at,
            rejection_reason=latest_triage.rejection_reason,
            created_at=latest_triage.created_at,
            proposed_actions=top_actions,
        )

    dup_items = []
    for d in issue.duplicates:
        cand = d.candidate_issue
        if cand:
            dup_items.append(
                DuplicateItem(
                    id=d.id,
                    candidate_issue_id=cand.id,
                    candidate_iid=cand.iid,
                    candidate_title=cand.title,
                    candidate_web_url=cand.web_url,
                    similarity_score=d.similarity_score,
                    comparison_notes=d.comparison_notes,
                )
            )

    notes = [IssueNoteSchema.model_validate(n) for n in sorted(issue.notes, key=lambda n: n.created_at)]
    eff_priority = (latest_triage.priority if latest_triage else None) or issue.priority

    return IssueDetailResponse(
        id=issue.id,
        gitlab_id=issue.gitlab_id,
        project_id=issue.project_id,
        iid=issue.iid,
        title=issue.title,
        description=issue.sanitized_description or issue.description,
        redaction_applied=issue.redaction_applied,
        state=issue.state,
        author_username=issue.author_username,
        author_name=issue.author_name,
        author_avatar_url=issue.author_avatar_url,
        labels=issue.labels or [],
        web_url=issue.web_url,
        status=issue.status,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
        triaged_at=issue.triaged_at,
        sla=_build_sla_countdown(issue, eff_priority),
        triage=triage_detail,
        proposed_actions=top_actions,
        notes=notes,
        duplicates=dup_items,
    )


@router.post("/{issue_id}/approve", response_model=ApproveActionsResponse)
async def approve_issue_actions(
    issue_id: UUID,
    payload: ApproveActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Approve & Execute proposed actions (posting draft comment, updating GitLab labels, or escalating).
    """
    stmt = (
        select(TriageAssessment)
        .where(TriageAssessment.issue_id == issue_id)
        .order_by(desc(TriageAssessment.created_at))
    )
    res = await db.execute(stmt)
    triage = res.scalars().first()

    if not triage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No triage assessment found for this issue")

    results = await triage_service.execute_approved_actions(
        db=db,
        triage_id=triage.id,
        actor="user:operator",
        edited_reply=payload.edited_reply,
        custom_labels=payload.custom_labels,
    )

    normalized: List[ActionExecutionResultItem] = []
    for item in results:
        raw_status = str(item.get("status", "EXECUTED")).upper()
        if raw_status not in ("DRAFT", "APPROVED", "EXECUTED", "FAILED", "REJECTED"):
            raw_status = "EXECUTED"
        normalized.append(
            ActionExecutionResultItem(
                action_id=UUID(str(item["action_id"])),
                action_type=item["type"],
                status=raw_status,  # type: ignore[arg-type]
                error=item.get("error"),
            )
        )

    return ApproveActionsResponse(
        status="success",
        executed_actions=normalized,
        golden_example_created=bool(payload.edited_reply or payload.override_category or payload.override_priority),
    )


@router.post("/{issue_id}/reject", response_model=RejectTriageResponse)
async def reject_issue_triage(
    issue_id: UUID,
    payload: Optional[RejectTriageRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Rejects the AI proposal and flags the issue for manual human resolution.
    """
    stmt = (
        select(Issue)
        .where(Issue.id == issue_id)
        .options(selectinload(Issue.triage_assessments).selectinload(TriageAssessment.proposed_actions))
    )
    res = await db.execute(stmt)
    issue = res.scalar_one_or_none()

    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    reason = (payload.reason if payload else None) or "Manually rejected by support engineer"
    if issue.triage_assessments:
        latest = issue.triage_assessments[-1]
        latest.approval_status = "rejected"
        latest.rejection_reason = reason
        for action in latest.proposed_actions:
            if action.status in ("DRAFT", "APPROVED"):
                action.status = "REJECTED"

    issue.status = "human_review"
    await db.commit()

    return RejectTriageResponse(
        status="rejected",
        message="Issue moved to manual human review",
        issue_id=issue.id,
    )


@router.post("/{issue_id}/clone", response_model=CloneIssueResponse)
async def clone_issue(
    issue_id: UUID,
    req: CloneIssueRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Clones or escalates an issue to a downstream project with prefilled templates and backlinks.
    """
    stmt = select(Issue).where(Issue.id == issue_id)
    res = await db.execute(stmt)
    issue = res.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    title = req.new_title or f"[Cloned] {issue.title}"
    body = issue.sanitized_description or issue.description or ""
    if req.additional_context:
        body += f"\n\n### Operator Notes:\n{req.additional_context}"

    labels = list(issue.labels or []) if req.inherit_labels else ["cloned"]

    result = gitlab_manager.clone_or_escalate_issue(
        source_project_id=issue.project_id,
        source_issue_iid=issue.iid,
        target_project_id=req.target_project_id,
        title=title,
        description=body,
        labels=labels,
    )

    audit = AuditLog(
        entity_type="issue",
        entity_id=str(issue.id),
        actor="user:operator",
        event="issue_cloned",
        details={"target_project_id": req.target_project_id, "cloned_result": result},
    )
    db.add(audit)
    await db.commit()

    return CloneIssueResponse(
        status="cloned",
        target=ClonedTargetIssue(**result),
    )


@router.post("/{issue_id}/re-triage", response_model=ReTriageResponse)
async def retriage_issue(issue_id: UUID, db: AsyncSession = Depends(get_db)):
    """Force re-run AI triage with updated runbooks or prompt parameters."""
    stmt = select(Issue).where(Issue.id == issue_id)
    res = await db.execute(stmt)
    issue = res.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    assessment = await triage_service.triage_issue(db, issue)
    return ReTriageResponse(
        status="retriaged",
        triage_id=assessment.id,
        confidence=assessment.confidence,
    )
