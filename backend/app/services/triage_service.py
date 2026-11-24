import time
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.entities import Issue, TriageAssessment, ProposedAction, AuditLog
from app.rag.embeddings import embedding_service
from app.rag.hybrid_retriever import hybrid_retriever
from app.services.llm_client import llm_client
from app.services.duplicate_detector import duplicate_detector
from app.gitlab.client import gitlab_manager
from app.core.config import settings


class TriageService:
    def sanitize_description(self, raw: str) -> str:
        """Strip raw base64 images, truncate massive stack traces, and clean HTML."""
        if not raw:
            return ""
        import re
        # Remove markdown images
        text = re.sub(r"!\[.*?\]\(.*?\)", "[Image Removed]", raw)
        # Truncate giant code fences to avoid context explosion
        def repl(match):
            m = match.group(0)
            if len(m) > 1000:
                return m[:1000] + "\n... [Stack trace truncated for LLM]"
            return m
        text = re.sub(r"```[\s\S]*?```", repl, text)
        return text[:3000].strip()

    async def triage_issue(self, db: AsyncSession, issue: Issue) -> TriageAssessment:
        """
        Executes the full end-to-end AI triage pipeline for a GitLab issue.
        """
        start_time = time.time()
        print(f"🚀 [Triage Pipeline] Starting analysis for Issue #{issue.iid} ({issue.title})")

        # 1. Sanitize text
        clean_desc = self.sanitize_description(issue.description or "")
        issue.sanitized_description = clean_desc

        # 2. Compute issue vector embedding
        full_text = f"{issue.title}\n{clean_desc[:500]}"
        issue_embedding = await embedding_service.get_embedding(full_text)
        issue.embedding = issue_embedding
        await db.commit()

        # 3. Detect duplicate candidates
        duplicates = await duplicate_detector.find_duplicates(db, issue)
        dup_summary = ""
        if duplicates:
            dup_summary = "\n".join(
                [f"- #{d['candidate_iid']}: {d['candidate_title']} ({int(d['similarity_score']*100)}% match)" for d in duplicates]
            )

        # 4. Hybrid RAG retrieval from Documentation and Academy
        query = f"{issue.title} {clean_desc[:200]}"
        doc_citations = await hybrid_retriever.retrieve(db, query=query, top_k=4)

        # 5. Invoke LLM for structured classification and technical draft
        llm_output = await llm_client.generate_triage(
            title=issue.title,
            description=clean_desc,
            author=issue.author_username,
            labels=issue.labels,
            doc_citations=doc_citations,
            duplicate_info=dup_summary
        )

        # 6. Determine Human Approval vs. Auto-Pilot
        # High confidence + auto-execution enabled -> Auto-Pilot; otherwise Co-Pilot
        is_high_confidence = llm_output.confidence >= settings.AUTO_PILOT_CONFIDENCE_THRESHOLD
        requires_human = not (is_high_confidence and settings.ENABLE_AUTO_EXECUTION)

        approval_status = "pending"
        if not requires_human:
            approval_status = "auto_executed"

        # 7. Create Triage Assessment Record
        assessment = TriageAssessment(
            issue_id=issue.id,
            category=llm_output.category,
            priority=llm_output.priority,
            component=llm_output.component,
            confidence=round(llm_output.confidence, 2),
            summary=llm_output.summary,
            root_cause_analysis=llm_output.root_cause_analysis,
            draft_reply_markdown=llm_output.draft_reply_markdown,
            suggested_labels=llm_output.suggested_labels,
            cited_docs=doc_citations,
            requires_human_approval=requires_human,
            approval_status=approval_status
        )
        db.add(assessment)
        await db.flush()

        # 8. Create Proposed Actions
        # Action A: Add labels
        action_labels = ProposedAction(
            triage_id=assessment.id,
            action_type="add_labels",
            payload={"labels": llm_output.suggested_labels + ["ai-triaged"]},
            is_destructive=False,
            status="executed" if not requires_human else "pending"
        )
        db.add(action_labels)

        # Action B: Post response note
        action_comment = ProposedAction(
            triage_id=assessment.id,
            action_type="comment",
            payload={"note_body": llm_output.draft_reply_markdown},
            is_destructive=False,
            status="executed" if not requires_human else "pending"
        )
        db.add(action_comment)

        # Action C: Downstream ticket if required
        if llm_output.requires_downstream_ticket:
            spec = llm_output.downstream_ticket_spec or {}
            action_escalate = ProposedAction(
                triage_id=assessment.id,
                action_type="escalate_downstream",
                payload={
                    "target_project_id": spec.get("target_project_id", issue.project_id),
                    "title": f"[Escalation] {issue.title}",
                    "description": spec.get("description", llm_output.root_cause_analysis),
                    "labels": ["escalated", "team::platform"]
                },
                is_destructive=True, # Mutating/escalation action always requires approval unless forced
                status="pending"
            )
            db.add(action_escalate)

        # Update issue status
        issue.status = "auto_resolved" if not requires_human else "pending_approval"
        issue.triaged_at = datetime.now(timezone.utc)

        # 9. If auto-pilot, execute immediately
        if not requires_human:
            try:
                gitlab_manager.update_labels(issue.project_id, issue.iid, llm_output.suggested_labels + ["ai-triaged"])
                gitlab_manager.add_comment(issue.project_id, issue.iid, llm_output.draft_reply_markdown)
                action_labels.executed_at = datetime.now(timezone.utc)
                action_comment.executed_at = datetime.now(timezone.utc)
            except Exception as e:
                print(f"Failed auto-execution: {e}")

        # 10. Audit Log
        duration_ms = int((time.time() - start_time) * 1000)
        audit = AuditLog(
            entity_type="triage",
            entity_id=str(assessment.id),
            actor="ai:gemini",
            event="triage_generated",
            details={
                "issue_iid": issue.iid,
                "project_id": issue.project_id,
                "confidence": llm_output.confidence,
                "requires_approval": requires_human,
                "duration_ms": duration_ms
            }
        )
        db.add(audit)
        await db.commit()

        print(f"✅ [Triage Pipeline] Completed Issue #{issue.iid} in {duration_ms}ms (Status: {issue.status})")
        return assessment

    async def execute_approved_actions(
        self,
        db: AsyncSession,
        triage_id: UUID,
        actor: str = "user:engineer",
        edited_reply: Optional[str] = None,
        custom_labels: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes human-approved actions (comment, labels, escalations) and logs to audit trail.
        """
        stmt = (
            select(TriageAssessment)
            .where(TriageAssessment.id == triage_id)
        )
        res = await db.execute(stmt)
        assessment = res.scalar_one_or_none()
        if not assessment:
            raise ValueError("Triage assessment not found")

        # Load issue
        stmt_issue = select(Issue).where(Issue.id == assessment.issue_id)
        res_issue = await db.execute(stmt_issue)
        issue = res_issue.scalar_one()

        # Load actions
        stmt_actions = select(ProposedAction).where(ProposedAction.triage_id == triage_id)
        res_actions = await db.execute(stmt_actions)
        actions = res_actions.scalars().all()

        results = []
        for action in actions:
            if action.status == "executed":
                continue

            try:
                if action.action_type == "comment":
                    body = edited_reply or action.payload.get("note_body", "")
                    comment_res = gitlab_manager.add_comment(issue.project_id, issue.iid, body)
                    action.status = "executed"
                    action.execution_result = comment_res
                    action.executed_at = datetime.now(timezone.utc)
                    results.append({"action_id": str(action.id), "type": "comment", "status": "executed"})

                elif action.action_type == "add_labels":
                    labels = custom_labels or action.payload.get("labels", [])
                    final_labels = list(set(labels + ["ai-triaged"]))
                    label_res = gitlab_manager.update_labels(issue.project_id, issue.iid, final_labels)
                    action.status = "executed"
                    action.execution_result = {"labels": label_res}
                    action.executed_at = datetime.now(timezone.utc)
                    results.append({"action_id": str(action.id), "type": "add_labels", "status": "executed"})

                elif action.action_type == "escalate_downstream":
                    p = action.payload
                    clone_res = gitlab_manager.clone_or_escalate_issue(
                        source_project_id=issue.project_id,
                        source_issue_iid=issue.iid,
                        target_project_id=p.get("target_project_id", issue.project_id),
                        title=p.get("title", f"[Escalated] {issue.title}"),
                        description=p.get("description", ""),
                        labels=p.get("labels", ["escalated"])
                    )
                    action.status = "executed"
                    action.execution_result = clone_res
                    action.executed_at = datetime.now(timezone.utc)
                    results.append({"action_id": str(action.id), "type": "escalate_downstream", "status": "executed"})

            except Exception as e:
                action.status = "failed"
                action.execution_error = str(e)
                results.append({"action_id": str(action.id), "type": action.action_type, "status": "failed", "error": str(e)})

        assessment.approval_status = "approved"
        assessment.approved_by = actor
        assessment.approved_at = datetime.now(timezone.utc)
        issue.status = "triaged"

        # Audit Log
        audit = AuditLog(
            entity_type="action",
            entity_id=str(assessment.id),
            actor=actor,
            event="action_approved_and_executed",
            details={"results": results}
        )
        db.add(audit)
        await db.commit()

        return results


triage_service = TriageService()
