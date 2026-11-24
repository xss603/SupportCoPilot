from fastapi import APIRouter, Depends
from sqlalchemy import select, asc
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.session import get_db
from app.models.entities import PlatformSetting, RoutingRule, SLAPolicy
from app.schemas.rules import PlatformRulesConfigSchema, RoutingRuleSchema, SLAPolicySchema

router = APIRouter(prefix="/rules", tags=["Rules & SLAs"])


@router.get("", response_model=PlatformRulesConfigSchema)
async def get_rules_config(db: AsyncSession = Depends(get_db)):
    """Retrieve platform thresholds, SLA policies, and category-to-project routing rules."""
    sla_res = await db.execute(select(SLAPolicy).order_by(asc(SLAPolicy.priority)))
    sla_policies = [SLAPolicySchema.model_validate(p) for p in sla_res.scalars().all()]

    rules_res = await db.execute(select(RoutingRule).order_by(asc(RoutingRule.priority_order)))
    routing_rules = [RoutingRuleSchema.model_validate(r) for r in rules_res.scalars().all()]

    settings_res = await db.execute(select(PlatformSetting))
    kv = {s.key: s.value for s in settings_res.scalars().all()}

    return PlatformRulesConfigSchema(
        auto_pilot_confidence_threshold=float(
            kv.get("auto_pilot_confidence_threshold", settings.AUTO_PILOT_CONFIDENCE_THRESHOLD)
        ),
        duplicate_similarity_threshold=float(
            kv.get("duplicate_similarity_threshold", settings.DUPLICATE_SIMILARITY_THRESHOLD)
        ),
        rag_min_confidence=float(kv.get("rag_min_confidence", settings.RAG_MIN_CONFIDENCE)),
        enable_auto_execution=bool(kv.get("enable_auto_execution", settings.ENABLE_AUTO_EXECUTION)),
        sla_policies=sla_policies,
        routing_rules=routing_rules,
    )


@router.put("", response_model=PlatformRulesConfigSchema)
async def update_rules_config(
    payload: PlatformRulesConfigSchema,
    db: AsyncSession = Depends(get_db),
):
    """Update platform thresholds, SLA policies, and routing rules (admin-only in M2)."""
    threshold_keys = {
        "auto_pilot_confidence_threshold": payload.auto_pilot_confidence_threshold,
        "duplicate_similarity_threshold": payload.duplicate_similarity_threshold,
        "rag_min_confidence": payload.rag_min_confidence,
        "enable_auto_execution": payload.enable_auto_execution,
    }
    for k, v in threshold_keys.items():
        res = await db.execute(select(PlatformSetting).where(PlatformSetting.key == k))
        existing = res.scalar_one_or_none()
        if existing:
            existing.value = v
        else:
            db.add(PlatformSetting(key=k, value=v))

    await db.commit()
    return await get_rules_config(db)
