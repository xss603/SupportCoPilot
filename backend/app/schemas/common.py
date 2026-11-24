from datetime import datetime
from typing import Literal
from pydantic import BaseModel

UserRole = Literal["reviewer", "admin"]

IssueStatus = Literal[
    "ingested",
    "triaging",
    "triaged",
    "auto_resolved",
    "pending_approval",
    "human_review",
    "closed",
]

IssueCategory = Literal[
    "bug",
    "feature_request",
    "configuration",
    "access_iam",
    "outage",
    "other",
]

PriorityLevel = Literal["P1", "P2", "P3", "P4"]

ProposedActionType = Literal[
    "comment",
    "add_labels",
    "clone_issue",
    "escalate_downstream",
    "close_issue",
]

ProposedActionStatus = Literal[
    "DRAFT",
    "APPROVED",
    "EXECUTED",
    "FAILED",
    "REJECTED",
]

ApprovalStatus = Literal["pending", "approved", "rejected", "auto_executed"]

SLAStatus = Literal["ok", "at_risk", "breached"]

CrawlerSourceType = Literal["runbooks", "documentation", "academy"]


class SLACountdown(BaseModel):
    priority: PriorityLevel
    target_minutes: int
    due_at: datetime
    remaining_seconds: int
    status: SLAStatus
    alert_sent: bool = False


class MessageResponse(BaseModel):
    status: str
    message: str
