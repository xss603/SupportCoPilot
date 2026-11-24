from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class GitLabUser(BaseModel):
    id: int
    name: str
    username: str
    avatar_url: Optional[str] = None
    email: Optional[str] = None


class GitLabProject(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    web_url: str
    path_with_namespace: Optional[str] = None


class GitLabLabel(BaseModel):
    id: Optional[int] = None
    title: str
    color: Optional[str] = None
    description: Optional[str] = None


class GitLabIssueAttributes(BaseModel):
    id: int
    iid: int
    title: str
    description: Optional[str] = ""
    state: str
    action: Optional[str] = None  # open, reopen, update, close
    created_at: str
    updated_at: Optional[str] = None
    url: str


class GitLabNoteAttributes(BaseModel):
    id: int
    note: str
    noteable_type: Optional[str] = None
    internal: bool = False
    created_at: Optional[str] = None
    url: Optional[str] = None


class GitLabWebhookEvent(BaseModel):
    object_kind: str  # issue, note
    event_type: Optional[str] = None
    user: GitLabUser
    project: GitLabProject
    object_attributes: Dict[str, Any]
    labels: List[Any] = Field(default_factory=list)
    changes: Optional[Dict[str, Any]] = None


class WebhookResponse(BaseModel):
    status: Literal["accepted", "ignored", "duplicate_ignored"]
    message: str
    issue_id: Optional[str] = None
    iid: Optional[int] = None
    reason: Optional[str] = None
