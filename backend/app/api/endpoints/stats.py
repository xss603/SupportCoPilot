import asyncio
import json
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_factory, get_db
from app.models.entities import AuditLog, DocsDriftCluster, Issue, TriageAssessment
from app.schemas.triage import DashboardStatsResponse, RecentActivityItem

router = APIRouter(prefix="/stats", tags=["Dashboard & Telemetry"])


@router.get("", response_model=DashboardStatsResponse)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Computes real-time KPI metrics for the Command Center overview."""
    res_total = await db.execute(select(func.count(Issue.id)))
    total_issues = res_total.scalar_one() or 0

    res_auto = await db.execute(select(func.count(Issue.id)).where(Issue.status == "auto_resolved"))
    auto_triaged = res_auto.scalar_one() or 0

    res_pending = await db.execute(select(func.count(Issue.id)).where(Issue.status == "pending_approval"))
    pending_approvals = res_pending.scalar_one() or 0

    res_at_risk = await db.execute(select(func.count(Issue.id)).where(Issue.sla_status == "at_risk"))
    sla_at_risk_count = res_at_risk.scalar_one() or 0

    res_breached = await db.execute(select(func.count(Issue.id)).where(Issue.sla_status == "breached"))
    sla_breached_count = res_breached.scalar_one() or 0

    res_drift = await db.execute(
        select(func.count(DocsDriftCluster.id)).where(DocsDriftCluster.status == "open")
    )
    docs_drift_clusters_count = res_drift.scalar_one() or 0

    res_latency = await db.execute(select(func.avg(TriageAssessment.latency_ms)))
    avg_ms = res_latency.scalar_one()
    avg_latency_s = round(float(avg_ms) / 1000.0, 2) if avg_ms is not None else 0.0

    auto_pilot_pct = round((auto_triaged / total_issues * 100), 1) if total_issues > 0 else 0.0

    cat_stmt = select(TriageAssessment.category, func.count(TriageAssessment.id)).group_by(TriageAssessment.category)
    res_cats = await db.execute(cat_stmt)
    category_dist = {row[0]: row[1] for row in res_cats.all()}

    prio_stmt = select(TriageAssessment.priority, func.count(TriageAssessment.id)).group_by(TriageAssessment.priority)
    res_prios = await db.execute(prio_stmt)
    priority_dist = {row[0]: row[1] for row in res_prios.all()}

    audit_stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(10)
    res_audits = await db.execute(audit_stmt)
    recent_activity = [
        RecentActivityItem(
            id=str(a.id),
            actor=a.actor,
            event=a.event,
            entity_type=a.entity_type,
            details=a.details or {},
            timestamp=a.created_at.isoformat(),
        )
        for a in res_audits.scalars().all()
    ]

    return DashboardStatsResponse(
        total_issues_ingested=total_issues,
        auto_triaged_count=auto_triaged,
        pending_approvals_count=pending_approvals,
        auto_pilot_percentage=auto_pilot_pct,
        avg_triage_latency_seconds=avg_latency_s,
        sla_at_risk_count=sla_at_risk_count,
        sla_breached_count=sla_breached_count,
        docs_drift_clusters_count=docs_drift_clusters_count,
        at_risk_issues=[],
        category_distribution=category_dist,
        priority_distribution=priority_dist,
        recent_activity=recent_activity,
    )


@router.get("/events")
async def stream_live_events(cursor: str | None = Query(default=None)):
    """
    Server-Sent Events (SSE) endpoint to push real-time activity and pipeline stage updates.
    """
    async def event_generator():
        last_check_id = cursor
        while True:
            try:
                async with async_session_factory() as db:
                    stmt = select(AuditLog).order_by(desc(AuditLog.created_at), desc(AuditLog.id)).limit(1)
                    res = await db.execute(stmt)
                    latest = res.scalar_one_or_none()

                    if latest and str(latest.id) != last_check_id:
                        last_check_id = str(latest.id)
                        payload = {
                            "id": str(latest.id),
                            "event": latest.event,
                            "actor": latest.actor,
                            "entity_type": latest.entity_type,
                            "entity_id": latest.entity_id,
                            "details": latest.details or {},
                            "timestamp": latest.created_at.isoformat(),
                        }
                        yield f"id: {latest.id}\nevent: pipeline_event\ndata: {json.dumps(payload)}\n\n"
                    else:
                        yield "event: heartbeat\ndata: {}\n\n"
            except Exception:
                yield "event: heartbeat\ndata: {}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
