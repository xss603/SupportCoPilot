from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.entities import GoldenExample
from app.schemas.common import MessageResponse
from app.schemas.rules import GoldenExampleSchema

router = APIRouter(prefix="/feedback", tags=["Feedback & Golden Examples"])


@router.get("/golden-examples", response_model=List[GoldenExampleSchema])
async def list_golden_examples(
    category: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List captured human-edited golden few-shot examples."""
    stmt = select(GoldenExample).order_by(desc(GoldenExample.created_at)).limit(limit).offset(offset)
    if category:
        stmt = stmt.where(GoldenExample.final_category == category)
    res = await db.execute(stmt)
    return [GoldenExampleSchema.model_validate(item) for item in res.scalars().all()]


@router.delete("/golden-examples/{example_id}", response_model=MessageResponse)
async def delete_golden_example(
    example_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a golden few-shot example (admin-only in M2)."""
    res = await db.execute(select(GoldenExample).where(GoldenExample.id == example_id))
    example = res.scalar_one_or_none()
    if not example:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Golden example not found")
    await db.delete(example)
    await db.commit()
    return MessageResponse(status="deleted", message=f"Golden example {example_id} deleted")
