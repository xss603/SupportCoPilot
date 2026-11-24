from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.common import (
    ApprovalStatus,
    IssueCategory,
    IssueStatus,
    PriorityLevel,
    ProposedActionStatus,
    ProposedActionType,
    SLACountdown,
)


class CitedDocItem(BaseModel):
    title: str
    url: str
    section: Optional[str] = None
    excerpt: str
    score: float


class DiagnosticCommand(BaseModel):
    label: str
    command: str
    language: str = "bash"
    description: Optional[str] = None


class DiagnosticRunbook(BaseModel):
    title: str
    summary: Optional[str] = None
    steps: List[str] = Field(default_factory=list)
    commands: List[DiagnosticCommand] = Field(default_factory=list)
    read_only_verified: bool = True


class IssueNoteSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    gitlab_note_id: int
    author_username: str
    author_name: Optional[str] = None
    author_avatar_url: Optional[str] = None
    body: str
    is_internal: bool = False
    is_bot: bool = False
    created_at: datetime


class ProposedActionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action_type: ProposedActionType
    payload: Dict[str, Any]
    is_destructive: bool
    status: ProposedActionStatus
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    retry_count: int = 0
    execution_result: Optional[Dict[str, Any]] = None
    execution_error: Optional[str] = None
    executed_at: Optional[datetime] = None
    created_at: datetime


class DuplicateItem(BaseModel):
    id: UUID
    candidate_issue_id: UUID
    candidate_iid: int
    candidate_title: str
    candidate_web_url: str
    similarity_score: float
    comparison_notes: Optional[str] = None


class TriageAssessmentDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: IssueCategory
    priority: PriorityLevel
    component: str
    confidence: float
    rag_max_score: Optional[float] = None
    abstained: bool = False
    redaction_applied: bool = False
    summary: str
    root_cause_analysis: Optional[str] = None
    draft_reply_markdown: str
    suggested_labels: List[str]
    cited_docs: List[CitedDocItem] = Field(default_factory=list)
    diagnostic_runbook: Optional[DiagnosticRunbook] = None
    latency_ms: Optional[int] = None
    requires_human_approval: bool
    approval_status: ApprovalStatus
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    proposed_actions: List[ProposedActionSchema] = Field(default_factory=list)


class IssueDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    gitlab_id: int
    project_id: int
    iid: int
    title: str
    description: Optional[str] = None
    redaction_applied: bool = False
    state: str
    author_username: str
    author_name: Optional[str] = None
    author_avatar_url: Optional[str] = None
    labels: List[str]
    web_url: str
    status: IssueStatus
    created_at: datetime
    updated_at: datetime
    triaged_at: Optional[datetime] = None
    sla: Optional[SLACountdown] = None
    triage: Optional[TriageAssessmentDetail] = None
    proposed_actions: List[ProposedActionSchema] = Field(default_factory=list)
    notes: List[IssueNoteSchema] = Field(default_factory=list)
    duplicates: List[DuplicateItem] = Field(default_factory=list)


class IssueListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: int
    iid: int
    title: str
    state: str
    author_username: str
    labels: List[str]
    web_url: str
    status: IssueStatus
    category: Optional[IssueCategory] = None
    priority: Optional[PriorityLevel] = None
    component: Optional[str] = None
    confidence: Optional[float] = None
    abstained: bool = False
    requires_approval: bool = False
    sla: Optional[SLACountdown] = None
    created_at: datetime


class ApproveActionRequest(BaseModel):
    action_ids: Optional[List[UUID]] = None
    edited_reply: Optional[str] = None
    custom_labels: Optional[List[str]] = None
    override_category: Optional[IssueCategory] = None
    override_priority: Optional[PriorityLevel] = None


class ActionExecutionResultItem(BaseModel):
    action_id: UUID
    action_type: ProposedActionType
    status: ProposedActionStatus
    execution_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ApproveActionsResponse(BaseModel):
    status: str
    executed_actions: List[ActionExecutionResultItem]
    golden_example_created: bool = False


class ActionExecutionResponse(BaseModel):
    status: str
    action: ProposedActionSchema


class RejectTriageRequest(BaseModel):
    reason: Optional[str] = None


class RejectTriageResponse(BaseModel):
    status: str
    message: str
    issue_id: UUID


class CloneIssueRequest(BaseModel):
    target_project_id: int
    new_title: Optional[str] = None
    additional_context: Optional[str] = None
    inherit_labels: bool = True
    cross_link: bool = True
    execute_immediately: bool = False
    source_issue_id: Optional[UUID] = None


class ClonedTargetIssue(BaseModel):
    id: int
    iid: int
    project_id: int
    title: str
    web_url: str


class CloneIssueResponse(BaseModel):
    status: str
    target: Optional[ClonedTargetIssue] = None
    proposed_action: Optional[ProposedActionSchema] = None


class ReTriageResponse(BaseModel):
    status: str
    triage_id: UUID
    confidence: float


class RecentActivityItem(BaseModel):
    id: str
    actor: str
    event: str
    entity_type: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str


class DashboardStatsResponse(BaseModel):
    total_issues_ingested: int
    auto_triaged_count: int
    pending_approvals_count: int
    auto_pilot_percentage: float
    avg_triage_latency_seconds: float
    sla_at_risk_count: int = 0
    sla_breached_count: int = 0
    docs_drift_clusters_count: int = 0
    at_risk_issues: List[IssueListItem] = Field(default_factory=list)
    category_distribution: Dict[str, int]
    priority_distribution: Dict[str, int]
    recent_activity: List[RecentActivityItem]
