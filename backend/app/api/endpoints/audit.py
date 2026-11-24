from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.entities import AuditLog
from app.schemas.rules import AuditLogSchema

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=List[AuditLogSchema])
async def list_audit_logs(
    entity_type: Optional[str] = None,
    event: Optional[str] = None,
    actor: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve immutable audit trail entries."""
    stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)
    conditions = []
    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)
    if event:
        conditions.append(AuditLog.event == event)
    if actor:
        conditions.append(AuditLog.actor == actor)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    res = await db.execute(stmt)
    return [AuditLogSchema.model_validate(item) for item in res.scalars().all()]
