from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.common import CrawlerSourceType


class DocChunkItem(BaseModel):
    id: UUID
    source_type: str
    title: str
    source_url: str
    section_header: Optional[str] = None
    content_preview: str
    created_at: datetime


class CrawlRequest(BaseModel):
    source_type: CrawlerSourceType = "runbooks"
    url: Optional[str] = None


class CrawlTriggerResponse(BaseModel):
    status: str
    message: str
    sync_run_id: Optional[UUID] = None


class CrawlerSyncRunSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    base_url: str
    pages_crawled: int
    chunks_indexed: int
    status: Literal["running", "completed", "failed"]
    error_message: Optional[str] = None
    triggered_by: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None


class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = 5
    source_type: Optional[str] = None


class RAGQueryResultItem(BaseModel):
    title: str
    source_url: str
    section_header: Optional[str] = None
    content: str
    similarity_score: float
    source_type: str


class RAGPlaygroundResponse(BaseModel):
    results: List[RAGQueryResultItem]
    max_score: float
    abstained: bool


class DocsDriftClusterSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cluster_label: str
    topic_summary: str
    issue_count: int
    avg_confidence: float
    sample_issue_ids: List[UUID] = Field(default_factory=list)
    status: Literal["open", "draft_generated", "resolved", "dismissed"]
    generated_doc_title: Optional[str] = None
    generated_doc_draft: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocDraftResponse(BaseModel):
    cluster_id: UUID
    title: str
    markdown_draft: str
    status: str
