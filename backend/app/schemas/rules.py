from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.common import IssueCategory, PriorityLevel


class SLAPolicySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None
    priority: PriorityLevel
    target_response_minutes: int
    target_resolution_minutes: int
    warning_threshold_pct: int = Field(default=75, ge=1, le=99)
    notify_slack: bool = True
    notify_gitlab_mention: bool = False
    escalation_mentions: List[str] = Field(default_factory=list)
    updated_at: Optional[datetime] = None


class RoutingRuleSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None
    name: str
    category: Optional[IssueCategory] = None
    component: Optional[str] = None
    priority: Optional[PriorityLevel] = None
    target_project_id: int
    target_project_name: Optional[str] = None
    auto_labels: List[str] = Field(default_factory=list)
    is_active: bool = True
    priority_order: int = 100


class PlatformRulesConfigSchema(BaseModel):
    auto_pilot_confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    duplicate_similarity_threshold: float = Field(default=0.82, ge=0.0, le=1.0)
    rag_min_confidence: float = Field(default=0.65, ge=0.0, le=1.0)
    enable_auto_execution: bool = False
    sla_policies: List[SLAPolicySchema] = Field(default_factory=list)
    routing_rules: List[RoutingRuleSchema] = Field(default_factory=list)


class GoldenExampleSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    issue_id: Optional[UUID] = None
    triage_id: Optional[UUID] = None
    issue_title: str
    sanitized_issue_excerpt: str
    original_category: Optional[str] = None
    final_category: str
    original_priority: Optional[str] = None
    final_priority: str
    original_labels: List[str] = Field(default_factory=list)
    final_labels: List[str] = Field(default_factory=list)
    original_reply: Optional[str] = None
    edited_reply: str
    diff_summary: Optional[str] = None
    created_by: str
    created_at: datetime


class AuditLogSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: str
    entity_id: str
    actor: str
    event: str
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    created_at: datetime
