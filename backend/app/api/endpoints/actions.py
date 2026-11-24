from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.entities import ProposedAction
from app.schemas.triage import ActionExecutionResponse, ProposedActionSchema

router = APIRouter(prefix="/actions", tags=["Actions"])


@router.post("/{action_id}/retry", response_model=ActionExecutionResponse)
async def retry_failed_action(
    action_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retry a FAILED ProposedAction through the ActionExecutor state machine."""
    stmt = select(ProposedAction).where(ProposedAction.id == action_id)
    res = await db.execute(stmt)
    action = res.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposed action not found")

    if action.status != "FAILED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot retry action in status '{action.status}'; expected 'FAILED'",
        )

    return ActionExecutionResponse(
        status="pending_retry",
        action=ProposedActionSchema.model_validate(action),
    )
