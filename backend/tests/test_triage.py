import pytest
from app.services.triage_service import triage_service
from app.schemas.triage import IssueListItem, TriageAssessmentDetail
from app.services.llm_client import LLMTriageOutput


def test_sanitize_description():
    raw_desc = (
        "Here is a markdown image ![diagram](https://example.com/bad.png) and some text.\n"
        "```bash\n" + "long log line\n" * 150 + "```\n"
        "And normal text."
    )
    cleaned = triage_service.sanitize_description(raw_desc)
    assert "[Image Removed]" in cleaned
    assert "[Stack trace truncated for LLM]" in cleaned
    assert len(cleaned) <= 3000


def test_llm_triage_output_schema():
    sample_json = {
        "category": "bug",
        "priority": "P1",
        "component": "Istio",
        "confidence": 0.94,
        "summary": "mTLS handshake failure on ingress",
        "root_cause_analysis": "DestinationRule missing STRICT mode",
        "draft_reply_markdown": "Check your DestinationRule configuration.",
        "suggested_labels": ["team::networking", "type::bug"],
        "requires_downstream_ticket": False
    }
    output = LLMTriageOutput(**sample_json)
    assert output.confidence == 0.94
    assert output.category == "bug"
    assert output.priority == "P1"
