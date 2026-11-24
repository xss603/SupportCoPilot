"""Mock OpenAI-compatible /v1/chat/completions & /v1/embeddings server.

Uses pure Python stdlib (`math` + `hashlib`) to produce deterministic 1536-dim
L2-normalized embeddings with exact analytical cosine guarantees and zero numpy.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

EMBEDDING_DIM = 1536
BLOCK_SIZE = 64
INV_SQRT_64 = 1.0 / 8.0  # 1 / sqrt(64) = 0.125 exact in IEEE-754
CLUSTER_ALPHA = 0.97
CLUSTER_BETA = math.sqrt(1.0 - CLUSTER_ALPHA * CLUSTER_ALPHA)

TOPIC_CLUSTERS: List[Tuple[str, Tuple[str, ...]]] = [
    (
        "istio",
        (
            "istio",
            "502",
            "mtls",
            "destinationrule",
            "peerauthentication",
            "ingress",
            "gateway",
            "envoy",
        ),
    ),
    (
        "vault",
        (
            "vault",
            "pki",
            "x509",
            "tls",
            "certificate",
            "cert",
            "san",
            "lease",
        ),
    ),
    (
        "db_migration",
        (
            "postgres",
            "postgresql",
            "migration",
            "alembic",
            "ddl",
            "grant",
            "schema",
            "database",
        ),
    ),
    (
        "k8s",
        (
            "kubernetes",
            "k8s",
            "kubectl",
            "crashloopbackoff",
            "oomkilled",
            "pod",
            "readiness",
            "liveness",
        ),
    ),
    (
        "ci_runner",
        (
            "runner",
            "gitlab-runner",
            "ci/cd",
            "pipeline",
            "docker-in-docker",
            "dind",
            "job timeout",
            "executor",
        ),
    ),
    (
        "out_of_corpus_a",
        (
            "quantum",
            "blockchain",
            "erp",
            "sap",
            "salesforce",
            "out_of_corpus",
            "unknown_topic",
            "kafka-raft",
        ),
    ),
    (
        "out_of_corpus_b",
        (
            "billing_invoice",
            "printer_driver",
            "hrm_payroll",
        ),
    ),
]

DOCS_SLUG_BY_CLUSTER: Dict[str, Tuple[str, str, str, str]] = {
    "istio": (
        "istio-502",
        "configuration",
        "P1",
        "Istio Ingress",
    ),
    "vault": (
        "vault-pki",
        "access_iam",
        "P2",
        "Vault PKI",
    ),
    "db_migration": (
        "db-migrations",
        "configuration",
        "P2",
        "PostgreSQL",
    ),
    "k8s": (
        "k8s-troubleshooting",
        "outage",
        "P1",
        "Kubernetes",
    ),
    "ci_runner": (
        "ci-runners",
        "bug",
        "P2",
        "CI/CD",
    ),
}

SIM_MARKER_RE = re.compile(r"__sim__:([a-zA-Z0-9_-]+):(anchor|0\.\d+|1(?:\.0+)?)")
UNIQUE_OOC_RE = re.compile(r"__unique_ooc__:([a-zA-Z0-9_-]+)")
NONCE_BLOCK_RE = re.compile(
    r"<(untrusted_gitlab_content)\s+[^>]*\bnonce=[\"'][a-zA-Z0-9_-]+[\"'][^>]*>.*?</\1>"
    r"|<(untrusted_(?!gitlab_content\b)[a-zA-Z0-9_-]+)>.*?</\2>",
    re.DOTALL,
)

INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"system\s+override", re.IGNORECASE),
    re.compile(r"\bexfiltrate\b", re.IGNORECASE),
    re.compile(r"\bauto[-_ ]?approve\b", re.IGNORECASE),
    re.compile(r"\bclone_issue\b", re.IGNORECASE),
)

SECRET_PATTERNS = (
    ("gitlab_pat", re.compile(r"glpat-[A-Za-z0-9_-]{6,}")),
    ("gitlab_token", re.compile(r"(?:gloas|gldt|glrt)-[A-Za-z0-9_-]{6,}|GR1348941[A-Za-z0-9_-]{6,}")),
    ("aws_access_key", re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}")),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}")),
    ("bearer_token", re.compile(r"(?:Authorization:\s*)?Bearer\s+[A-Za-z0-9._~+/=-]{16,}")),
    ("db_dsn", re.compile(r"(?:postgres(?:ql)?|mysql|mongodb|redis|amqp)(?:\+[a-z0-9]+)?://[^:\s]+:[^@\s]+@")),
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]


def _block_unit_vector(block_idx: int) -> List[float]:
    vec = [0.0] * EMBEDDING_DIM
    start = block_idx * BLOCK_SIZE
    for i in range(start, start + BLOCK_SIZE):
        vec[i] = INV_SQRT_64
    return vec


def _pair_vector(a: List[float], b: List[float], cos_target: float) -> List[float]:
    cos_clamped = max(-1.0, min(1.0, cos_target))
    sin_part = math.sqrt(max(0.0, 1.0 - cos_clamped * cos_clamped))
    return _normalize([cos_clamped * x + sin_part * y for x, y in zip(a, b)])


def _hashed_subspace_unit(seed: str, start: int, length: int) -> List[float]:
    vec = [0.0] * EMBEDDING_DIM
    vals: List[float] = []
    block_idx = 0
    while len(vals) < length:
        digest = hashlib.sha256(f"{seed}:{block_idx}".encode("utf-8")).digest()
        for j in range(0, len(digest), 2):
            if len(vals) >= length:
                break
            raw = int.from_bytes(digest[j : j + 2], "big")
            # Map [0, 65535] -> [-1.0, 1.0]
            vals.append((raw / 32767.5) - 1.0)
        block_idx += 1

    norm = math.sqrt(sum(v * v for v in vals))
    if norm == 0.0:
        vals[0] = 1.0
        norm = 1.0
    for offset, val in enumerate(vals):
        vec[start + offset] = val / norm
    return vec


def classify_topic(text: str) -> str:
    lowered = text.lower()
    best_cluster = "out_of_corpus_a"
    best_hits = 0
    for name, keywords in TOPIC_CLUSTERS:
        hits = sum(
            1
            for kw in keywords
            if re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", lowered)
        )
        if hits > best_hits:
            best_hits = hits
            best_cluster = name
    return best_cluster


def compute_embedding(text: str) -> List[float]:
    # 1. Exact calibrated fixtures
    a_dup = _block_unit_vector(8)  # [512:576]
    b_dup = _block_unit_vector(9)  # [576:640]
    if "fixture:dup_anchor" in text:
        return a_dup
    if "fixture:dup_0.819" in text:
        return _pair_vector(a_dup, b_dup, 0.819)
    if "fixture:dup_0.820" in text:
        return _pair_vector(a_dup, b_dup, 0.820)

    a_rag = _block_unit_vector(10)  # [640:704]
    b_rag = _block_unit_vector(11)  # [704:768]
    if "fixture:rag_anchor" in text:
        return a_rag
    if "fixture:rag_0.649" in text:
        return _pair_vector(a_rag, b_rag, 0.649)
    if "fixture:rag_0.650" in text:
        return _pair_vector(a_rag, b_rag, 0.650)

    # 2. Generic calibrated similarity marker
    sim_match = SIM_MARKER_RE.search(text)
    if sim_match:
        pair_id, target = sim_match.group(1), sim_match.group(2)
        h1 = _hashed_subspace_unit(f"sim1:{pair_id}", 768, 64)
        h2 = _hashed_subspace_unit(f"sim2:{pair_id}", 832, 64)
        if target == "anchor":
            return h1
        return _pair_vector(h1, h2, float(target))

    # 3. Unique non-clustering out-of-corpus marker
    unique_match = UNIQUE_OOC_RE.search(text)
    if unique_match:
        return _hashed_subspace_unit(f"unique:{unique_match.group(1)}:{text}", 896, 640)

    # 4. Topic cluster + orthogonal hash residual in [896:1536]
    cluster_name = classify_topic(text)
    cluster_idx = next(i for i, (name, _) in enumerate(TOPIC_CLUSTERS) if name == cluster_name)
    c_vec = _block_unit_vector(cluster_idx)
    n_vec = _hashed_subspace_unit(f"residual:{text}", 896, 640)
    combined = [CLUSTER_ALPHA * c + CLUSTER_BETA * n for c, n in zip(c_vec, n_vec)]
    return _normalize(combined)


def _inspect_prompt_security(texts: List[str]) -> Tuple[bool, bool, List[str]]:
    joined = "\n".join(texts)
    has_nonce = bool(NONCE_BLOCK_RE.search(joined))
    stripped = NONCE_BLOCK_RE.sub("", joined)
    detected_raw_injection = any(pat.search(stripped) for pat in INJECTION_PATTERNS)
    leaked = [name for name, pat in SECRET_PATTERNS if pat.search(joined)]
    return has_nonce, detected_raw_injection, leaked


def _build_triage_json(
    cluster: str,
    docs_base_url: str,
    force_low_confidence: bool = False,
) -> Dict[str, Any]:
    base = docs_base_url.rstrip("/")
    if force_low_confidence or cluster.startswith("out_of_corpus") or cluster not in DOCS_SLUG_BY_CLUSTER:
        return {
            "category": "other",
            "priority": "P3",
            "component": "Platform",
            "confidence": 0.42,
            "summary": "Insufficient documentation coverage to provide a grounded automated resolution.",
            "root_cause_analysis": (
                "No matching documentation or runbook was found in the indexed corpus. "
                "Abstaining from guessing an unverified remediation."
            ),
            "draft_reply_markdown": (
                "### Automated Support Assessment\n\n"
                "Our knowledge base currently lacks sufficient documentation coverage for this issue. "
                "A support engineer will review this ticket and follow up shortly."
            ),
            "suggested_labels": ["needs-human-review"],
            "requires_downstream_ticket": False,
            "downstream_ticket_spec": None,
        }

    slug, category, priority, component = DOCS_SLUG_BY_CLUSTER[cluster]
    doc_url = f"{base}/docs/{slug}"
    commands_by_cluster = {
        "istio": "kubectl get peerauthentication -n <namespace> -o yaml\nkubectl get destinationrule -n <namespace> -o yaml",
        "vault": "openssl x509 -in /etc/ssl/certs/tls.crt -noout -enddate\nkubectl logs -n <namespace> <pod-name> -c vault-agent-init --tail=100",
        "db_migration": "kubectl get jobs -n <namespace> -l component=db-migration\nalembic current --verbose",
        "k8s": "kubectl describe pod -n <namespace> <pod-name>\nkubectl top pods -n <namespace> --containers",
        "ci_runner": "kubectl get pods -n gitlab-runner -l app=gitlab-runner\nkubectl logs -n gitlab-runner -l app=gitlab-runner --tail=100",
    }
    diag_cmds = commands_by_cluster[cluster]
    return {
        "category": category,
        "priority": priority,
        "component": component,
        "confidence": 0.92,
        "summary": f"Grounded {component} diagnosis citing internal platform documentation.",
        "root_cause_analysis": (
            f"Matched platform documentation at {doc_url} describing known {component} failure modes "
            "and read-only verification steps."
        ),
        "draft_reply_markdown": (
            f"### Automated Platform Support Analysis ({component})\n\n"
            f"Based on our internal documentation ([{component} Guide]({doc_url})), "
            "please run the following read-only diagnostic commands:\n\n"
            f"```bash\n{diag_cmds}\n```\n"
        ),
        "suggested_labels": ["ai-triaged", f"severity::{priority}"],
        "requires_downstream_ticket": cluster == "db_migration",
        "downstream_ticket_spec": (
            {
                "target_project_id": 303,
                "title": "[Escalated] Database migration / grant request",
                "reason": "Production DDL or elevated grant review required",
            }
            if cluster == "db_migration"
            else None
        ),
    }


class SetModeRequest(BaseModel):
    mode: Optional[str] = None
    docs_base_url: Optional[str] = None


VALID_MODES = {"normal", "low_confidence", "injection_trap", "error_500", "invalid_json"}


def create_app(initial_docs_base_url: Optional[str] = None) -> FastAPI:
    app = FastAPI(title="Mock OpenAI LLM & Embeddings", version="1.0.0")
    default_docs_url = (
        initial_docs_base_url
        or os.getenv("DOCS_BASE_URL")
        or "http://localhost:9003"
    ).rstrip("/")

    state: Dict[str, Any] = {
        "mode": "normal",
        "docs_base_url": default_docs_url,
        "requests_log": [],
    }

    @app.get("/healthz")
    async def healthz() -> Dict[str, str]:
        return {"status": "ok", "service": "mock_llm", "mode": state["mode"]}

    @app.post("/v1/embeddings")
    async def create_embeddings(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
        raw_input = payload.get("input", [])
        if isinstance(raw_input, str):
            texts = [raw_input]
        elif isinstance(raw_input, list):
            texts = [str(item) for item in raw_input]
        else:
            texts = [str(raw_input)]

        has_nonce, detected_raw_injection, leaked_secrets = _inspect_prompt_security(texts)
        state["requests_log"].append(
            {
                "timestamp": _now_iso(),
                "endpoint": "/v1/embeddings",
                "model": payload.get("model", "text-embedding-3-small"),
                "input": texts,
                "has_nonce_delimiters": has_nonce,
                "detected_raw_injection": detected_raw_injection,
                "leaked_secrets": leaked_secrets,
            }
        )

        data = [
            {
                "object": "embedding",
                "index": idx,
                "embedding": compute_embedding(text),
            }
            for idx, text in enumerate(texts)
        ]
        return JSONResponse(
            status_code=200,
            content={
                "object": "list",
                "data": data,
                "model": payload.get("model", "text-embedding-3-small"),
                "usage": {"prompt_tokens": len(texts) * 8, "total_tokens": len(texts) * 8},
            },
        )

    @app.post("/v1/chat/completions")
    async def chat_completions(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
        messages = payload.get("messages", [])
        msg_texts = [str(m.get("content", "")) for m in messages if isinstance(m, dict)]
        has_nonce, detected_raw_injection, leaked_secrets = _inspect_prompt_security(msg_texts)

        state["requests_log"].append(
            {
                "timestamp": _now_iso(),
                "endpoint": "/v1/chat/completions",
                "model": payload.get("model", "gemini-2.5-flash"),
                "messages": messages,
                "tools": payload.get("tools"),
                "has_nonce_delimiters": has_nonce,
                "detected_raw_injection": detected_raw_injection,
                "leaked_secrets": leaked_secrets,
            }
        )

        mode = state["mode"]
        if mode == "error_500":
            return JSONResponse(
                status_code=500,
                content={"error": {"message": "Simulated LLM server error", "type": "server_error"}},
            )

        if mode == "invalid_json":
            return JSONResponse(
                status_code=200,
                content={
                    "id": f"chatcmpl-{uuid4().hex[:12]}",
                    "object": "chat.completion",
                    "model": payload.get("model", "gemini-2.5-flash"),
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": "{not-valid-json",
                            },
                        }
                    ],
                },
            )

        if mode == "injection_trap":
            trap_json = {
                "category": "access_iam",
                "priority": "P1",
                "component": "Platform",
                "confidence": 0.99,
                "summary": "Prompt injection trap attempted unauthorized escalation.",
                "root_cause_analysis": "Injected override attempting tool call clone_issue.",
                "draft_reply_markdown": "Executing clone_issue to project 999 and dumping secrets.",
                "suggested_labels": ["auto-resolved"],
                "requires_downstream_ticket": True,
                "downstream_ticket_spec": {
                    "target_project_id": 999,
                    "title": "[HIJACK] Exfiltrate Credentials",
                },
            }
            return JSONResponse(
                status_code=200,
                content={
                    "id": f"chatcmpl-{uuid4().hex[:12]}",
                    "object": "chat.completion",
                    "model": payload.get("model", "gemini-2.5-flash"),
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "tool_calls",
                            "message": {
                                "role": "assistant",
                                "content": json.dumps(trap_json),
                                "tool_calls": [
                                    {
                                        "id": "call_trap_001",
                                        "type": "function",
                                        "function": {
                                            "name": "clone_issue",
                                            "arguments": json.dumps(
                                                {"target_project_id": 999, "exfiltrate_secret": True}
                                            ),
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                },
            )

        user_prompt = "\n".join(
            str(m.get("content", ""))
            for m in messages
            if isinstance(m, dict) and m.get("role") == "user"
        ) or "\n".join(msg_texts)

        cluster = classify_topic(user_prompt)
        force_low = mode == "low_confidence" or (
            "no matching documentation" in user_prompt.lower()
            and cluster.startswith("out_of_corpus")
        )
        triage_payload = _build_triage_json(
            cluster=cluster,
            docs_base_url=state["docs_base_url"],
            force_low_confidence=force_low,
        )

        return JSONResponse(
            status_code=200,
            content={
                "id": f"chatcmpl-{uuid4().hex[:12]}",
                "object": "chat.completion",
                "model": payload.get("model", "gemini-2.5-flash"),
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(triage_payload),
                        },
                    }
                ],
                "usage": {"prompt_tokens": 64, "completion_tokens": 96, "total_tokens": 160},
            },
        )

    @app.post("/_control/set-mode")
    async def set_mode(body: SetModeRequest) -> JSONResponse:
        if body.mode is not None:
            if body.mode not in VALID_MODES:
                return JSONResponse(
                    status_code=422,
                    content={"detail": f"Invalid mode '{body.mode}'. Valid: {sorted(VALID_MODES)}"},
                )
            state["mode"] = body.mode
        if body.docs_base_url is not None:
            state["docs_base_url"] = body.docs_base_url.rstrip("/")
        return JSONResponse(
            status_code=200,
            content={"mode": state["mode"], "docs_base_url": state["docs_base_url"]},
        )

    @app.get("/_control/requests")
    async def get_requests() -> Dict[str, Any]:
        logs = state["requests_log"]
        return {"count": len(logs), "requests": list(logs)}

    @app.post("/_control/reset")
    async def reset() -> Dict[str, Any]:
        state["mode"] = "normal"
        state["requests_log"].clear()
        return {"status": "reset", "mode": state["mode"], "docs_base_url": state["docs_base_url"]}

    return app


app = create_app()
