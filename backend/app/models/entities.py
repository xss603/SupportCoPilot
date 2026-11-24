import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.db.session import Base
from app.core.config import settings


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Issue(Base):
    __tablename__ = "issues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    gitlab_id = Column(BigInteger, nullable=False)
    project_id = Column(BigInteger, nullable=False)
    iid = Column(Integer, nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    sanitized_description = Column(Text, nullable=True)
    redaction_applied = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    state = Column(String(50), nullable=False, default="opened", server_default=text("'opened'"))
    author_username = Column(String(255), nullable=False)
    author_name = Column(String(255), nullable=True)
    author_avatar_url = Column(Text, nullable=True)
    labels = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    web_url = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="ingested", server_default=text("'ingested'"))
    priority = Column(String(10), nullable=True)
    sla_due_at = Column(DateTime(timezone=True), nullable=True)
    sla_status = Column(String(20), nullable=True)

    # 1536-dimensional vector for duplicate and semantic lookup
    embedding = Column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=True)

    gitlab_created_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=text("now()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=text("now()"), nullable=False)
    triaged_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    triage_assessments = relationship("TriageAssessment", back_populates="issue", cascade="all, delete-orphan")
    notes = relationship("IssueNote", back_populates="issue", cascade="all, delete-orphan")
    sla_alerts = relationship("SLAAlert", back_populates="issue", cascade="all, delete-orphan")
    duplicates = relationship(
        "DuplicateCandidate",
        foreign_keys="DuplicateCandidate.issue_id",
        back_populates="issue",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("project_id", "iid", name="uq_issues_project_iid"),
        CheckConstraint(
            "status IN ('ingested','triaging','triaged','auto_resolved','pending_approval','human_review','closed')",
            name="ck_issues_status",
        ),
        CheckConstraint("priority IS NULL OR priority IN ('P1','P2','P3','P4')", name="ck_issues_priority"),
        CheckConstraint("sla_status IS NULL OR sla_status IN ('ok','at_risk','breached')", name="ck_issues_sla_status"),
        Index("idx_issues_gitlab_id", "gitlab_id"),
        Index("idx_issues_project_id", "project_id"),
        Index("idx_issues_status", "status"),
        Index("idx_issues_priority", "priority"),
        Index("idx_issues_sla_due_at", "sla_due_at"),
        Index("idx_issues_created_at", "created_at"),
        Index(
            "idx_issues_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class IssueNote(Base):
    __tablename__ = "issue_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    issue_id = Column(UUID(as_uuid=True), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)
    gitlab_note_id = Column(BigInteger, nullable=False)
    author_username = Column(String(255), nullable=False)
    author_name = Column(String(255), nullable=True)
    author_avatar_url = Column(Text, nullable=True)
    body = Column(Text, nullable=False)
    sanitized_body = Column(Text, nullable=True)
    is_bot = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    is_internal = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=text("now()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=text("now()"), nullable=False)

    issue = relationship("Issue", back_populates="notes")

    __table_args__ = (
        UniqueConstraint("issue_id", "gitlab_note_id", name="uq_issue_notes_issue_gitlab_note"),
        Index("idx_issue_notes_issue_id", "issue_id"),
        Index("idx_issue_notes_created_at", "created_at"),
    )


class TriageAssessment(Base):
    __tablename__ = "triage_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    issue_id = Column(UUID(as_uuid=True), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)

    category = Column(String(100), nullable=False)
    priority = Column(String(50), nullable=False)
    component = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False)
    rag_max_score = Column(Float, nullable=True)
    abstained = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    redaction_applied = Column(Boolean, nullable=False, default=False, server_default=text("false"))

    summary = Column(Text, nullable=False)
    root_cause_analysis = Column(Text, nullable=True)
    draft_reply_markdown = Column(Text, nullable=False)
    suggested_labels = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    cited_docs = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    diagnostic_runbook = Column(JSONB, nullable=True)
    latency_ms = Column(Integer, nullable=True)

    requires_human_approval = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    approval_status = Column(String(50), nullable=False, default="pending", server_default=text("'pending'"))
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=text("now()"), nullable=False)

    issue = relationship("Issue", back_populates="triage_assessments")
    proposed_actions = relationship("ProposedAction", back_populates="triage", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "category IN ('bug','feature_request','configuration','access_iam','outage','other')",
            name="ck_triage_category",
        ),
        CheckConstraint("priority IN ('P1','P2','P3','P4')", name="ck_triage_priority"),
        CheckConstraint(
            "approval_status IN ('pending','approved','rejected','auto_executed')",
            name="ck_triage_approval_status",
        ),
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_triage_confidence"),
        Index("idx_triage_issue_id", "issue_id"),
        Index("idx_triage_category", "category"),
        Index("idx_triage_priority", "priority"),
        Index("idx_triage_created_at", "created_at"),
    )


class ProposedAction(Base):
    __tablename__ = "proposed_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    triage_id = Column(UUID(as_uuid=True), ForeignKey("triage_assessments.id", ondelete="CASCADE"), nullable=False)

    action_type = Column(String(100), nullable=False)
    payload = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    is_destructive = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    status = Column(String(50), nullable=False, default="DRAFT", server_default=text("'DRAFT'"))
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    execution_result = Column(JSONB, nullable=True)
    execution_error = Column(Text, nullable=True)
    executed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=text("now()"), nullable=False)

    triage = relationship("TriageAssessment", back_populates="proposed_actions")

    __table_args__ = (
        CheckConstraint(
            "action_type IN ('comment','add_labels','clone_issue','escalate_downstream','close_issue')",
            name="ck_proposed_action_type",
        ),
        CheckConstraint(
            "status IN ('DRAFT','APPROVED','EXECUTED','FAILED','REJECTED')",
            name="ck_proposed_action_status",
        ),
        Index("idx_proposed_actions_triage_id", "triage_id"),
        Index("idx_proposed_actions_status", "status"),
    )


class DuplicateCandidate(Base):
    __tablename__ = "duplicate_candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    issue_id = Column(UUID(as_uuid=True), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)
    candidate_issue_id = Column(UUID(as_uuid=True), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)

    similarity_score = Column(Float, nullable=False)
    comparison_notes = Column(Text, nullable=True)
    is_confirmed_duplicate = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=text("now()"), nullable=False)

    issue = relationship("Issue", foreign_keys=[issue_id], back_populates="duplicates")
    candidate_issue = relationship("Issue", foreign_keys=[candidate_issue_id])

    __table_args__ = (
        UniqueConstraint("issue_id", "candidate_issue_id", name="uq_duplicate_pair"),
        CheckConstraint("issue_id <> candidate_issue_id", name="ck_duplicate_not_self"),
        Index("idx_duplicate_issue_id", "issue_id"),
        Index("idx_duplicate_candidate_id", "candidate_issue_id"),
    )


class DocChunk(Base):
    __tablename__ = "doc_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    source_type = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    source_url = Column(Text, nullable=False)
    section_header = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=True)
    metadata_json = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))

    embedding = Column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=False)
    search_vector = Column(TSVECTOR, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=text("now()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=text("now()"), nullable=False)

    __table_args__ = (
        CheckConstraint("source_type IN ('documentation','academy','runbook')", name="ck_doc_chunks_source_type"),
        Index("idx_doc_chunks_source_type", "source_type"),
        Index("idx_doc_chunks_source_url", "source_url"),
        Index("idx_doc_chunks_search_vector", "search_vector", postgresql_using="gin"),
        Index(
            "idx_doc_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class CrawlerSyncRun(Base):
    __tablename__ = "crawler_sync_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    source = Column(String(100), nullable=False)
    base_url = Column(Text, nullable=False)
    pages_crawled = Column(Integer, nullable=False, default=0, server_default=text("0"))
    chunks_indexed = Column(Integer, nullable=False, default=0, server_default=text("0"))
    status = Column(String(50), nullable=False, default="running", server_default=text("'running'"))
    error_message = Column(Text, nullable=True)
    triggered_by = Column(String(255), nullable=True)
    started_at = Column(DateTime(timezone=True), default=utc_now, server_default=text("now()"), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('running','completed','failed')", name="ck_crawler_sync_status"),
        Index("idx_crawler_sync_runs_started_at", "started_at"),
    )


class DocsDriftCluster(Base):
    __tablename__ = "docs_drift_clusters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    cluster_label = Column(String(255), nullable=False)
    topic_summary = Column(Text, nullable=False)
    issue_count = Column(Integer, nullable=False, default=1, server_default=text("1"))
    avg_confidence = Column(Float, nullable=False)
    sample_issue_ids = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    centroid_embedding = Column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=True)
    status = Column(String(50), nullable=False, default="open", server_default=text("'open'"))
    generated_doc_title = Column(String(500), nullable=True)
    generated_doc_draft = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=text("now()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=text("now()"), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('open','draft_generated','resolved','dismissed')",
            name="ck_drift_cluster_status",
        ),
        Index("idx_drift_clusters_status", "status"),
        Index(
            "idx_docs_drift_centroid_hnsw",
            "centroid_embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"centroid_embedding": "vector_cosine_ops"},
        ),
    )


class GoldenExample(Base):
    __tablename__ = "golden_examples"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    issue_id = Column(UUID(as_uuid=True), ForeignKey("issues.id", ondelete="SET NULL"), nullable=True)
    triage_id = Column(UUID(as_uuid=True), ForeignKey("triage_assessments.id", ondelete="SET NULL"), nullable=True)
    issue_title = Column(String(500), nullable=False)
    sanitized_issue_excerpt = Column(Text, nullable=False)
    original_category = Column(String(100), nullable=True)
    final_category = Column(String(100), nullable=False)
    original_priority = Column(String(50), nullable=True)
    final_priority = Column(String(50), nullable=False)
    original_labels = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    final_labels = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    original_reply = Column(Text, nullable=True)
    edited_reply = Column(Text, nullable=False)
    diff_summary = Column(Text, nullable=True)
    created_by = Column(String(255), nullable=False)
    embedding = Column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=text("now()"), nullable=False)

    __table_args__ = (
        Index("idx_golden_examples_created_at", "created_at"),
        Index("idx_golden_examples_category", "final_category"),
        Index(
            "idx_golden_examples_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class SLAPolicy(Base):
    __tablename__ = "sla_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    priority = Column(String(10), nullable=False)
    target_response_minutes = Column(Integer, nullable=False)
    target_resolution_minutes = Column(Integer, nullable=False)
    warning_threshold_pct = Column(Integer, nullable=False, default=75, server_default=text("75"))
    notify_slack = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    notify_gitlab_mention = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    escalation_mentions = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    updated_by = Column(String(255), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=text("now()"), nullable=False)

    __table_args__ = (
        UniqueConstraint("priority", name="uq_sla_policies_priority"),
        CheckConstraint("priority IN ('P1','P2','P3','P4')", name="ck_sla_policy_priority"),
        CheckConstraint("warning_threshold_pct >= 1 AND warning_threshold_pct <= 99", name="ck_sla_warning_pct"),
    )


class SLAAlert(Base):
    __tablename__ = "sla_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    issue_id = Column(UUID(as_uuid=True), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)
    sla_policy_id = Column(UUID(as_uuid=True), ForeignKey("sla_policies.id", ondelete="SET NULL"), nullable=True)
    priority = Column(String(10), nullable=False)
    alert_type = Column(String(50), nullable=False)
    channel = Column(String(50), nullable=False)
    recipient = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)
    delivered = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), default=utc_now, server_default=text("now()"), nullable=False)

    issue = relationship("Issue", back_populates="sla_alerts")

    __table_args__ = (
        UniqueConstraint("issue_id", "priority", "alert_type", "channel", name="uq_sla_alerts_dedup"),
        CheckConstraint("alert_type IN ('pre_breach','breached')", name="ck_sla_alert_type"),
        CheckConstraint("channel IN ('slack','mattermost','gitlab_mention')", name="ck_sla_alert_channel"),
        Index("idx_sla_alerts_issue_id", "issue_id"),
        Index("idx_sla_alerts_sent_at", "sent_at"),
    )


class RoutingRule(Base):
    __tablename__ = "routing_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    component = Column(String(100), nullable=True)
    priority = Column(String(50), nullable=True)
    target_project_id = Column(BigInteger, nullable=False)
    target_project_name = Column(String(255), nullable=True)
    auto_labels = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    priority_order = Column(Integer, nullable=False, default=100, server_default=text("100"))
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=text("now()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=text("now()"), nullable=False)

    __table_args__ = (
        Index("idx_routing_rules_active_order", "is_active", "priority_order"),
    )


class PlatformSetting(Base):
    __tablename__ = "platform_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    key = Column(String(100), nullable=False)
    value = Column(JSONB, nullable=False)
    description = Column(Text, nullable=True)
    updated_by = Column(String(255), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=text("now()"), nullable=False)

    __table_args__ = (
        UniqueConstraint("key", name="uq_platform_settings_key"),
    )


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    event_uuid = Column(String(255), nullable=True)
    payload_sha256 = Column(String(64), nullable=False)
    object_kind = Column(String(50), nullable=False)
    project_id = Column(BigInteger, nullable=True)
    issue_iid = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False, default="accepted", server_default=text("'accepted'"))
    received_at = Column(DateTime(timezone=True), default=utc_now, server_default=text("now()"), nullable=False)

    __table_args__ = (
        UniqueConstraint("event_uuid", name="uq_webhook_deliveries_event_uuid"),
        Index("idx_webhook_deliveries_sha256", "payload_sha256"),
        Index("idx_webhook_deliveries_received_at", "received_at"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(255), nullable=False)
    actor = Column(String(255), nullable=False, default="system", server_default=text("'system'"))
    event = Column(String(100), nullable=False)
    details = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    ip_address = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=text("now()"), nullable=False)

    __table_args__ = (
        Index("idx_audit_logs_entity_id", "entity_id"),
        Index("idx_audit_logs_created_at", "created_at"),
        Index("idx_audit_logs_created_at_id", "created_at", "id"),
    )
