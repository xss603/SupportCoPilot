"""Initial 15-table pgvector schema, HNSW/GIN indexes, and triggers.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-24 12:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # 2. Table 1: issues
    op.create_table(
        "issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("gitlab_id", sa.BigInteger(), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("iid", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sanitized_description", sa.Text(), nullable=True),
        sa.Column("redaction_applied", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("state", sa.String(length=50), server_default=sa.text("'opened'"), nullable=False),
        sa.Column("author_username", sa.String(length=255), nullable=False),
        sa.Column("author_name", sa.String(length=255), nullable=True),
        sa.Column("author_avatar_url", sa.Text(), nullable=True),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("web_url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'ingested'"), nullable=False),
        sa.Column("priority", sa.String(length=10), nullable=True),
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sla_status", sa.String(length=20), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("gitlab_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("triaged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "iid", name="uq_issues_project_iid"),
        sa.CheckConstraint(
            "status IN ('ingested','triaging','triaged','auto_resolved','pending_approval','human_review','closed')",
            name="ck_issues_status",
        ),
        sa.CheckConstraint("priority IS NULL OR priority IN ('P1','P2','P3','P4')", name="ck_issues_priority"),
        sa.CheckConstraint("sla_status IS NULL OR sla_status IN ('ok','at_risk','breached')", name="ck_issues_sla_status"),
    )
    op.create_index("idx_issues_gitlab_id", "issues", ["gitlab_id"])
    op.create_index("idx_issues_project_id", "issues", ["project_id"])
    op.create_index("idx_issues_status", "issues", ["status"])
    op.create_index("idx_issues_priority", "issues", ["priority"])
    op.create_index("idx_issues_sla_due_at", "issues", ["sla_due_at"])
    op.create_index("idx_issues_created_at", "issues", ["created_at"])

    # 3. Table 2: issue_notes
    op.create_table(
        "issue_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gitlab_note_id", sa.BigInteger(), nullable=False),
        sa.Column("author_username", sa.String(length=255), nullable=False),
        sa.Column("author_name", sa.String(length=255), nullable=True),
        sa.Column("author_avatar_url", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("sanitized_body", sa.Text(), nullable=True),
        sa.Column("is_bot", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_internal", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("issue_id", "gitlab_note_id", name="uq_issue_notes_issue_gitlab_note"),
    )
    op.create_index("idx_issue_notes_issue_id", "issue_notes", ["issue_id"])
    op.create_index("idx_issue_notes_created_at", "issue_notes", ["created_at"])

    # 4. Table 3: triage_assessments
    op.create_table(
        "triage_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("priority", sa.String(length=50), nullable=False),
        sa.Column("component", sa.String(length=100), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("rag_max_score", sa.Float(), nullable=True),
        sa.Column("abstained", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("redaction_applied", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("root_cause_analysis", sa.Text(), nullable=True),
        sa.Column("draft_reply_markdown", sa.Text(), nullable=False),
        sa.Column("suggested_labels", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("cited_docs", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("diagnostic_runbook", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("requires_human_approval", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("approval_status", sa.String(length=50), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "category IN ('bug','feature_request','configuration','access_iam','outage','other')",
            name="ck_triage_category",
        ),
        sa.CheckConstraint("priority IN ('P1','P2','P3','P4')", name="ck_triage_priority"),
        sa.CheckConstraint(
            "approval_status IN ('pending','approved','rejected','auto_executed')",
            name="ck_triage_approval_status",
        ),
        sa.CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_triage_confidence"),
    )
    op.create_index("idx_triage_issue_id", "triage_assessments", ["issue_id"])
    op.create_index("idx_triage_category", "triage_assessments", ["category"])
    op.create_index("idx_triage_priority", "triage_assessments", ["priority"])
    op.create_index("idx_triage_created_at", "triage_assessments", ["created_at"])

    # 5. Table 4: proposed_actions
    op.create_table(
        "proposed_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("triage_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("is_destructive", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'DRAFT'"), nullable=False),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("execution_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("execution_error", sa.Text(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["triage_id"], ["triage_assessments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "action_type IN ('comment','add_labels','clone_issue','escalate_downstream','close_issue')",
            name="ck_proposed_action_type",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT','APPROVED','EXECUTED','FAILED','REJECTED')",
            name="ck_proposed_action_status",
        ),
    )
    op.create_index("idx_proposed_actions_triage_id", "proposed_actions", ["triage_id"])
    op.create_index("idx_proposed_actions_status", "proposed_actions", ["status"])

    # 6. Table 5: duplicate_candidates
    op.create_table(
        "duplicate_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column("comparison_notes", sa.Text(), nullable=True),
        sa.Column("is_confirmed_duplicate", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_issue_id"], ["issues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("issue_id", "candidate_issue_id", name="uq_duplicate_pair"),
        sa.CheckConstraint("issue_id <> candidate_issue_id", name="ck_duplicate_not_self"),
    )
    op.create_index("idx_duplicate_issue_id", "duplicate_candidates", ["issue_id"])
    op.create_index("idx_duplicate_candidate_id", "duplicate_candidates", ["candidate_issue_id"])

    # 7. Table 6: doc_chunks
    op.create_table(
        "doc_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("section_header", sa.String(length=500), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("source_type IN ('documentation','academy','runbook')", name="ck_doc_chunks_source_type"),
    )
    op.create_index("idx_doc_chunks_source_type", "doc_chunks", ["source_type"])
    op.create_index("idx_doc_chunks_source_url", "doc_chunks", ["source_url"])

    # 8. Table 7: crawler_sync_runs
    op.create_table(
        "crawler_sync_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("pages_crawled", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("chunks_indexed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'running'"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("triggered_by", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status IN ('running','completed','failed')", name="ck_crawler_sync_status"),
    )
    op.create_index("idx_crawler_sync_runs_started_at", "crawler_sync_runs", ["started_at"])

    # 9. Table 8: docs_drift_clusters
    op.create_table(
        "docs_drift_clusters",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("cluster_label", sa.String(length=255), nullable=False),
        sa.Column("topic_summary", sa.Text(), nullable=False),
        sa.Column("issue_count", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("avg_confidence", sa.Float(), nullable=False),
        sa.Column("sample_issue_ids", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("centroid_embedding", Vector(1536), nullable=True),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'open'"), nullable=False),
        sa.Column("generated_doc_title", sa.String(length=500), nullable=True),
        sa.Column("generated_doc_draft", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('open','draft_generated','resolved','dismissed')",
            name="ck_drift_cluster_status",
        ),
    )
    op.create_index("idx_drift_clusters_status", "docs_drift_clusters", ["status"])

    # 10. Table 9: golden_examples
    op.create_table(
        "golden_examples",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("triage_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("issue_title", sa.String(length=500), nullable=False),
        sa.Column("sanitized_issue_excerpt", sa.Text(), nullable=False),
        sa.Column("original_category", sa.String(length=100), nullable=True),
        sa.Column("final_category", sa.String(length=100), nullable=False),
        sa.Column("original_priority", sa.String(length=50), nullable=True),
        sa.Column("final_priority", sa.String(length=50), nullable=False),
        sa.Column("original_labels", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("final_labels", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("original_reply", sa.Text(), nullable=True),
        sa.Column("edited_reply", sa.Text(), nullable=False),
        sa.Column("diff_summary", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["triage_id"], ["triage_assessments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_golden_examples_created_at", "golden_examples", ["created_at"])
    op.create_index("idx_golden_examples_category", "golden_examples", ["final_category"])

    # 11. Table 10: sla_policies
    op.create_table(
        "sla_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("priority", sa.String(length=10), nullable=False),
        sa.Column("target_response_minutes", sa.Integer(), nullable=False),
        sa.Column("target_resolution_minutes", sa.Integer(), nullable=False),
        sa.Column("warning_threshold_pct", sa.Integer(), server_default=sa.text("75"), nullable=False),
        sa.Column("notify_slack", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("notify_gitlab_mention", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("escalation_mentions", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("priority", name="uq_sla_policies_priority"),
        sa.CheckConstraint("priority IN ('P1','P2','P3','P4')", name="ck_sla_policy_priority"),
        sa.CheckConstraint("warning_threshold_pct >= 1 AND warning_threshold_pct <= 99", name="ck_sla_warning_pct"),
    )

    # 12. Table 11: sla_alerts
    op.create_table(
        "sla_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sla_policy_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("priority", sa.String(length=10), nullable=False),
        sa.Column("alert_type", sa.String(length=50), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("delivered", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sla_policy_id"], ["sla_policies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("issue_id", "priority", "alert_type", "channel", name="uq_sla_alerts_dedup"),
        sa.CheckConstraint("alert_type IN ('pre_breach','breached')", name="ck_sla_alert_type"),
        sa.CheckConstraint("channel IN ('slack','mattermost','gitlab_mention')", name="ck_sla_alert_channel"),
    )
    op.create_index("idx_sla_alerts_issue_id", "sla_alerts", ["issue_id"])
    op.create_index("idx_sla_alerts_sent_at", "sla_alerts", ["sent_at"])

    # 13. Table 12: routing_rules
    op.create_table(
        "routing_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("component", sa.String(length=100), nullable=True),
        sa.Column("priority", sa.String(length=50), nullable=True),
        sa.Column("target_project_id", sa.BigInteger(), nullable=False),
        sa.Column("target_project_name", sa.String(length=255), nullable=True),
        sa.Column("auto_labels", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("priority_order", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_routing_rules_active_order", "routing_rules", ["is_active", "priority_order"])

    # 14. Table 13: platform_settings
    op.create_table(
        "platform_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_platform_settings_key"),
    )

    # 15. Table 14: webhook_deliveries
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("event_uuid", sa.String(length=255), nullable=True),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("object_kind", sa.String(length=50), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=True),
        sa.Column("issue_iid", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'accepted'"), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_uuid", name="uq_webhook_deliveries_event_uuid"),
    )
    op.create_index("idx_webhook_deliveries_sha256", "webhook_deliveries", ["payload_sha256"])
    op.create_index("idx_webhook_deliveries_received_at", "webhook_deliveries", ["received_at"])

    # 16. Table 15: audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=255), nullable=False),
        sa.Column("actor", sa.String(length=255), server_default=sa.text("'system'"), nullable=False),
        sa.Column("event", sa.String(length=100), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("ip_address", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_logs_entity_id", "audit_logs", ["entity_id"])
    op.create_index("idx_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("idx_audit_logs_created_at_id", "audit_logs", ["created_at", "id"])

    # 17. HNSW cosine indexes & GIN FTS index
    op.execute(
        "CREATE INDEX idx_issues_embedding_hnsw ON issues "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )
    op.execute(
        "CREATE INDEX idx_doc_chunks_embedding_hnsw ON doc_chunks "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )
    op.execute(
        "CREATE INDEX idx_docs_drift_centroid_hnsw ON docs_drift_clusters "
        "USING hnsw (centroid_embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )
    op.execute(
        "CREATE INDEX idx_golden_examples_embedding_hnsw ON golden_examples "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )
    op.execute(
        "CREATE INDEX idx_doc_chunks_search_vector ON doc_chunks USING gin (search_vector)"
    )

    # 18. Trigger: Auto-populate doc_chunks.search_vector (weighted TSVECTOR)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION doc_chunks_update_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.section_header, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(NEW.content, '')), 'C');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_doc_chunks_search_vector
        BEFORE INSERT OR UPDATE OF title, section_header, content ON doc_chunks
        FOR EACH ROW
        EXECUTE FUNCTION doc_chunks_update_search_vector()
        """
    )

    # 19. Trigger: Immutable audit_logs (prevent UPDATE and DELETE)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only and immutable: % is not permitted', TG_OP;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_audit_logs_immutable
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_log_modification()
        """
    )

    # 20. Default SLA policies seed
    op.execute(
        """
        INSERT INTO sla_policies (priority, target_response_minutes, target_resolution_minutes, warning_threshold_pct, notify_slack, notify_gitlab_mention)
        VALUES
            ('P1', 15, 60, 75, true, true),
            ('P2', 60, 240, 75, true, false),
            ('P3', 240, 1440, 75, true, false),
            ('P4', 480, 4320, 75, false, false)
        ON CONFLICT (priority) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_modification()")
    op.execute("DROP TRIGGER IF EXISTS trg_doc_chunks_search_vector ON doc_chunks")
    op.execute("DROP FUNCTION IF EXISTS doc_chunks_update_search_vector()")

    op.drop_table("audit_logs")
    op.drop_table("webhook_deliveries")
    op.drop_table("platform_settings")
    op.drop_table("routing_rules")
    op.drop_table("sla_alerts")
    op.drop_table("sla_policies")
    op.drop_table("golden_examples")
    op.drop_table("docs_drift_clusters")
    op.drop_table("crawler_sync_runs")
    op.drop_table("doc_chunks")
    op.drop_table("duplicate_candidates")
    op.drop_table("proposed_actions")
    op.drop_table("triage_assessments")
    op.drop_table("issue_notes")
    op.drop_table("issues")
