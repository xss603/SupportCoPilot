"""Mock GitLab REST API v4 + Webhook Emitter compatible with python-gitlab==8.6.0."""

from __future__ import annotations

import asyncio
import math
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple
from uuid import uuid4

import httpx
from fastapi import APIRouter, Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_labels(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str):
        return [part.strip() for part in raw.split(",") if part.strip()]
    return [str(raw).strip()]


def _pagination_headers(
    request: Request,
    total: int,
    page: int,
    per_page: int,
) -> Dict[str, str]:
    total_pages = max(1, math.ceil(total / per_page)) if total > 0 else 1
    next_page = str(page + 1) if page < total_pages else ""
    prev_page = str(page - 1) if page > 1 else ""

    links: List[str] = []
    if page < total_pages:
        next_url = str(request.url.include_query_params(page=page + 1, per_page=per_page))
        links.append(f'<{next_url}>; rel="next"')
    if page > 1:
        prev_url = str(request.url.include_query_params(page=page - 1, per_page=per_page))
        links.append(f'<{prev_url}>; rel="prev"')
    first_url = str(request.url.include_query_params(page=1, per_page=per_page))
    last_url = str(request.url.include_query_params(page=total_pages, per_page=per_page))
    links.append(f'<{first_url}>; rel="first"')
    links.append(f'<{last_url}>; rel="last"')

    return {
        "X-Page": str(page),
        "X-Per-Page": str(per_page),
        "X-Total": str(total),
        "X-Total-Pages": str(total_pages),
        "X-Next-Page": next_page,
        "X-Prev-Page": prev_page,
        "Link": ", ".join(links),
    }


class EmitWebhookRequest(BaseModel):
    kind: Literal["issue", "note"] = "issue"
    target_url: str
    secret: str = ""
    event_uuid: Optional[str] = None
    project_id: int = 101
    issue_iid: Optional[int] = None
    action: str = "open"
    title: str = "502 Bad Gateway from Istio Ingress"
    description: str = (
        "Upstream delayed connect error 111 when PeerAuthentication is STRICT."
    )
    note_body: str = "Attached kubectl get destinationrule diagnostic output."
    author_username: Optional[str] = None
    labels: List[str] = Field(default_factory=list)
    upsert_in_store: bool = True
    deliver: bool = True


class SetRateLimitRequest(BaseModel):
    count: int = 1
    retry_after: int = 1


class SetTimeoutRequest(BaseModel):
    delay_ms: int = 0


class ResetRequest(BaseModel):
    seed: bool = True


def create_app() -> FastAPI:
    app = FastAPI(title="Mock GitLab REST API v4", version="1.0.0")

    def _build_initial_state(seed: bool = True) -> Dict[str, Any]:
        bot_username = os.getenv("GITLAB_BOT_USERNAME", "platform-support-bot")
        bot_user = {
            "id": 1,
            "username": bot_username,
            "name": "Platform Support Bot",
            "email": "bot@example.local",
            "avatar_url": None,
            "state": "active",
        }
        alice_user = {
            "id": 2,
            "username": "alice.dev",
            "name": "Alice Developer",
            "email": "alice@example.local",
            "avatar_url": None,
            "state": "active",
        }
        projects = {
            101: {
                "id": 101,
                "name": "platform-support",
                "path": "platform-support",
                "path_with_namespace": "support/platform-support",
                "description": "Primary internal platform support issue tracker",
                "default_branch": "main",
            },
            202: {
                "id": 202,
                "name": "infra-core",
                "path": "infra-core",
                "path_with_namespace": "platform/infra-core",
                "description": "Core Kubernetes, Istio, and Vault infrastructure",
                "default_branch": "main",
            },
            303: {
                "id": 303,
                "name": "data-eng",
                "path": "data-eng",
                "path_with_namespace": "platform/data-eng",
                "description": "PostgreSQL and Data Engineering platform requests",
                "default_branch": "main",
            },
            12345678: {
                "id": 12345678,
                "name": "default-project",
                "path": "default-project",
                "path_with_namespace": "support/default-project",
                "description": "Default configured GitLab support project",
                "default_branch": "main",
            },
            79988314: {
                "id": 79988314,
                "name": "cicd-helm-deploy",
                "path": "cicd-helm-deploy",
                "path_with_namespace": "caris4ops/cicd-helm-deploy",
                "description": "CI/CD and Helm deployment escalation repo",
                "default_branch": "main",
            },
            79988306: {
                "id": 79988306,
                "name": "vault-cert-automation",
                "path": "vault-cert-automation",
                "path_with_namespace": "caris4ops/vault-cert-automation",
                "description": "Vault PKI certificate automation repo",
                "default_branch": "main",
            },
        }
        default_labels = [
            {"id": 1, "name": "team::networking", "color": "#428BCA", "description": "Networking & Istio"},
            {"id": 2, "name": "team::security", "color": "#D9534F", "description": "Vault & Security"},
            {"id": 3, "name": "team::data", "color": "#5CB85C", "description": "PostgreSQL & Data"},
            {"id": 4, "name": "team::platform", "color": "#F0AD4E", "description": "Core Kubernetes"},
            {"id": 5, "name": "type::bug", "color": "#D9534F", "description": "Bug report"},
            {"id": 6, "name": "type::configuration", "color": "#5BC0DE", "description": "Configuration"},
            {"id": 7, "name": "severity::P1", "color": "#CC0033", "description": "Critical outage"},
            {"id": 8, "name": "severity::P2", "color": "#E67E22", "description": "High priority"},
            {"id": 9, "name": "ai-triaged", "color": "#69D100", "description": "Triaged by automation"},
            {"id": 10, "name": "auto-resolved", "color": "#2ECC71", "description": "Auto-resolved"},
            {"id": 11, "name": "needs-human-review", "color": "#F1C40F", "description": "Needs human review"},
            {"id": 12, "name": "escalated", "color": "#8E44AD", "description": "Escalated downstream"},
        ]

        issues: Dict[Tuple[int, int], Dict[str, Any]] = {}
        notes: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
        next_gitlab_id = 10000
        next_note_id = 50000

        if seed:
            seed_specs = [
                (
                    1,
                    "502 Bad Gateway on checkout service via Istio Ingress",
                    "Gateway returns 502 with delayed connect error 111 under PeerAuthentication STRICT.",
                    ["team::networking"],
                ),
                (
                    2,
                    "Vault PKI TLS certificate expired on payment-api",
                    "Pod tls.crt expired and vault-agent-init failed to renew lease.",
                    ["team::security"],
                ),
                (
                    3,
                    "Request GRANT ALL on production analytics postgres database",
                    "Need elevated DDL schema migration permissions on production analytics DB.",
                    ["team::data"],
                ),
                (
                    4,
                    "Kubernetes pod CrashLoopBackOff OOMKilled exit code 137",
                    "Worker container repeatedly restarted with OOMKilled exit code 137.",
                    ["team::platform"],
                ),
                (
                    5,
                    "GitLab CI runner dind Cannot connect to Docker daemon",
                    "Pipeline build job fails connecting to tcp://docker:2375 with TLS timeout.",
                    ["type::bug"],
                ),
            ]
            now = _now_iso()
            for iid, title, desc, lbls in seed_specs:
                next_gitlab_id += 1
                issues[(101, iid)] = {
                    "id": next_gitlab_id,
                    "iid": iid,
                    "project_id": 101,
                    "title": title,
                    "description": desc,
                    "state": "opened",
                    "created_at": now,
                    "updated_at": now,
                    "closed_at": None,
                    "labels": lbls,
                    "author": dict(alice_user),
                    "upvotes": 0,
                    "downvotes": 0,
                    "user_notes_count": 1 if iid == 1 else 0,
                }
                notes[(101, iid)] = []

            next_note_id += 1
            notes[(101, 1)].append(
                {
                    "id": next_note_id,
                    "body": "Initial customer trace attached from ingress gateway pod.",
                    "author": dict(alice_user),
                    "created_at": now,
                    "updated_at": now,
                    "system": False,
                    "noteable_id": issues[(101, 1)]["id"],
                    "noteable_iid": 1,
                    "noteable_type": "Issue",
                }
            )

        return {
            "bot_username": bot_username,
            "users": {
                bot_username: bot_user,
                "alice.dev": alice_user,
            },
            "projects": projects,
            "labels": {pid: list(default_labels) for pid in projects},
            "issues": issues,
            "notes": notes,
            "next_gitlab_id": next_gitlab_id,
            "next_note_id": next_note_id,
            "rate_limit": {"remaining_429": 0, "retry_after": 1},
            "timeout": {"delay_ms": 0},
            "emitted_webhooks": [],
            "api_requests": [],
        }

    state = _build_initial_state(seed=True)

    def _base_url(request: Request) -> str:
        return str(request.base_url).rstrip("/")

    def _resolve_project(project_ref: str) -> Dict[str, Any]:
        # Numeric ID
        if project_ref.isdigit():
            pid = int(project_ref)
            proj = state["projects"].get(pid)
            if proj:
                return proj
        # Namespace/path lookup
        normalized = project_ref.strip("/")
        for proj in state["projects"].values():
            if proj["path_with_namespace"] == normalized:
                return proj
        raise HTTPException(status_code=404, detail=f"Project '{project_ref}' not found")

    def _serialize_project(proj: Dict[str, Any], request: Request) -> Dict[str, Any]:
        base = _base_url(request)
        out = dict(proj)
        out["web_url"] = f"{base}/{proj['path_with_namespace']}"
        return out

    def _serialize_user(user: Dict[str, Any], request: Request) -> Dict[str, Any]:
        base = _base_url(request)
        out = dict(user)
        out["web_url"] = f"{base}/{user['username']}"
        return out

    def _serialize_issue(issue: Dict[str, Any], proj: Dict[str, Any], request: Request) -> Dict[str, Any]:
        base = _base_url(request)
        out = dict(issue)
        out["author"] = _serialize_user(issue["author"], request)
        out["web_url"] = f"{base}/{proj['path_with_namespace']}/-/issues/{issue['iid']}"
        out["labels"] = list(issue.get("labels", []))
        return out

    def _get_or_create_user(username: Optional[str]) -> Dict[str, Any]:
        uname = username or "alice.dev"
        existing = state["users"].get(uname)
        if existing:
            return existing
        new_user = {
            "id": len(state["users"]) + 10,
            "username": uname,
            "name": uname.replace(".", " ").title(),
            "email": f"{uname}@example.local",
            "avatar_url": None,
            "state": "active",
        }
        state["users"][uname] = new_user
        return new_user

    def _next_iid_for_project(pid: int) -> int:
        existing_iids = [iid for (p, iid) in state["issues"] if p == pid]
        return (max(existing_iids) + 1) if existing_iids else 1

    @app.middleware("http")
    async def gitlab_fault_injection_and_audit(request: Request, call_next: Any) -> Any:
        if request.url.path.startswith("/api/v4"):
            state["api_requests"].append(
                {
                    "timestamp": _now_iso(),
                    "method": request.method,
                    "path": request.url.path,
                    "query": dict(request.query_params),
                }
            )
            delay_ms = int(state["timeout"]["delay_ms"])
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000.0)
            if int(state["rate_limit"]["remaining_429"]) > 0:
                state["rate_limit"]["remaining_429"] -= 1
                retry_after = int(state["rate_limit"]["retry_after"])
                return JSONResponse(
                    status_code=429,
                    content={"message": "Retry later"},
                    headers={"Retry-After": str(retry_after)},
                )
        return await call_next(request)

    @app.get("/healthz")
    async def healthz() -> Dict[str, str]:
        return {"status": "ok", "service": "mock_gitlab"}

    api = APIRouter(prefix="/api/v4")

    @api.get("/user")
    async def get_current_user(request: Request) -> Dict[str, Any]:
        bot = state["users"][state["bot_username"]]
        return _serialize_user(bot, request)

    # --- Handlers shared between single-segment and namespace/project routes ---

    async def _list_issues(
        project_ref: str,
        request: Request,
        issue_state: Optional[str],
        labels: Optional[str],
        page: int,
        per_page: int,
    ) -> JSONResponse:
        proj = _resolve_project(project_ref)
        pid = proj["id"]
        matched = [
            issue
            for (p, _), issue in sorted(state["issues"].items(), key=lambda kv: kv[0][1])
            if p == pid
        ]
        if issue_state and issue_state != "all":
            matched = [i for i in matched if i["state"] == issue_state]
        if labels:
            required = set(_parse_labels(labels))
            matched = [i for i in matched if required.issubset(set(i.get("labels", [])))]

        total = len(matched)
        start = (page - 1) * per_page
        end = start + per_page
        page_items = [_serialize_issue(i, proj, request) for i in matched[start:end]]
        headers = _pagination_headers(request, total=total, page=page, per_page=per_page)
        return JSONResponse(status_code=200, content=page_items, headers=headers)

    async def _create_issue(
        project_ref: str,
        request: Request,
        payload: Dict[str, Any],
    ) -> JSONResponse:
        proj = _resolve_project(project_ref)
        pid = proj["id"]
        title = payload.get("title")
        if not title:
            raise HTTPException(status_code=400, detail="title is required")

        state["next_gitlab_id"] += 1
        iid = _next_iid_for_project(pid)
        now = _now_iso()
        author = state["users"][state["bot_username"]]
        issue = {
            "id": state["next_gitlab_id"],
            "iid": iid,
            "project_id": pid,
            "title": str(title),
            "description": str(payload.get("description") or ""),
            "state": "opened",
            "created_at": now,
            "updated_at": now,
            "closed_at": None,
            "labels": _parse_labels(payload.get("labels")),
            "author": dict(author),
            "confidential": bool(payload.get("confidential", False)),
            "upvotes": 0,
            "downvotes": 0,
            "user_notes_count": 0,
        }
        state["issues"][(pid, iid)] = issue
        state["notes"][(pid, iid)] = []
        return JSONResponse(status_code=201, content=_serialize_issue(issue, proj, request))

    async def _get_issue(project_ref: str, iid: int, request: Request) -> Dict[str, Any]:
        proj = _resolve_project(project_ref)
        issue = state["issues"].get((proj["id"], iid))
        if not issue:
            raise HTTPException(status_code=404, detail=f"Issue !{iid} not found")
        return _serialize_issue(issue, proj, request)

    async def _update_issue(
        project_ref: str,
        iid: int,
        request: Request,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        proj = _resolve_project(project_ref)
        issue = state["issues"].get((proj["id"], iid))
        if not issue:
            raise HTTPException(status_code=404, detail=f"Issue !{iid} not found")

        if "title" in payload and payload["title"] is not None:
            issue["title"] = str(payload["title"])
        if "description" in payload and payload["description"] is not None:
            issue["description"] = str(payload["description"])
        if "labels" in payload:
            issue["labels"] = _parse_labels(payload["labels"])
        if "state_event" in payload:
            ev = payload["state_event"]
            if ev == "close":
                issue["state"] = "closed"
                issue["closed_at"] = _now_iso()
            elif ev == "reopen":
                issue["state"] = "opened"
                issue["closed_at"] = None
        issue["updated_at"] = _now_iso()
        return _serialize_issue(issue, proj, request)

    async def _list_notes(
        project_ref: str,
        iid: int,
        request: Request,
        page: int,
        per_page: int,
    ) -> JSONResponse:
        proj = _resolve_project(project_ref)
        key = (proj["id"], iid)
        if key not in state["issues"]:
            raise HTTPException(status_code=404, detail=f"Issue !{iid} not found")
        all_notes = state["notes"].get(key, [])
        total = len(all_notes)
        start = (page - 1) * per_page
        end = start + per_page
        serialized = []
        for note in all_notes[start:end]:
            item = dict(note)
            item["author"] = _serialize_user(note["author"], request)
            serialized.append(item)
        headers = _pagination_headers(request, total=total, page=page, per_page=per_page)
        return JSONResponse(status_code=200, content=serialized, headers=headers)

    async def _create_note(
        project_ref: str,
        iid: int,
        request: Request,
        payload: Dict[str, Any],
    ) -> JSONResponse:
        proj = _resolve_project(project_ref)
        key = (proj["id"], iid)
        issue = state["issues"].get(key)
        if not issue:
            raise HTTPException(status_code=404, detail=f"Issue !{iid} not found")
        body = payload.get("body")
        if not body:
            raise HTTPException(status_code=400, detail="body is required")

        state["next_note_id"] += 1
        now = _now_iso()
        author = state["users"][state["bot_username"]]
        note = {
            "id": state["next_note_id"],
            "body": str(body),
            "author": dict(author),
            "created_at": now,
            "updated_at": now,
            "system": False,
            "noteable_id": issue["id"],
            "noteable_iid": iid,
            "noteable_type": "Issue",
        }
        state["notes"].setdefault(key, []).append(note)
        issue["user_notes_count"] = len(state["notes"][key])
        issue["updated_at"] = now

        out = dict(note)
        out["author"] = _serialize_user(author, request)
        return JSONResponse(status_code=201, content=out)

    async def _list_labels(
        project_ref: str,
        request: Request,
        page: int,
        per_page: int,
    ) -> JSONResponse:
        proj = _resolve_project(project_ref)
        all_labels = state["labels"].get(proj["id"], [])
        total = len(all_labels)
        start = (page - 1) * per_page
        end = start + per_page
        headers = _pagination_headers(request, total=total, page=page, per_page=per_page)
        return JSONResponse(status_code=200, content=all_labels[start:end], headers=headers)

    # Register specific sub-resource routes BEFORE /projects/{project_id:path}

    @api.get("/projects/{project_id}/issues/{iid}/notes")
    async def list_notes_single(
        project_id: str,
        iid: int,
        request: Request,
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
    ) -> JSONResponse:
        return await _list_notes(project_id, iid, request, page, per_page)

    @api.get("/projects/{namespace}/{project_name}/issues/{iid}/notes")
    async def list_notes_ns(
        namespace: str,
        project_name: str,
        iid: int,
        request: Request,
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
    ) -> JSONResponse:
        return await _list_notes(f"{namespace}/{project_name}", iid, request, page, per_page)

    @api.post("/projects/{project_id}/issues/{iid}/notes")
    async def create_note_single(
        project_id: str,
        iid: int,
        request: Request,
        payload: Dict[str, Any] = Body(...),
    ) -> JSONResponse:
        return await _create_note(project_id, iid, request, payload)

    @api.post("/projects/{namespace}/{project_name}/issues/{iid}/notes")
    async def create_note_ns(
        namespace: str,
        project_name: str,
        iid: int,
        request: Request,
        payload: Dict[str, Any] = Body(...),
    ) -> JSONResponse:
        return await _create_note(f"{namespace}/{project_name}", iid, request, payload)

    @api.get("/projects/{project_id}/issues/{iid}")
    async def get_issue_single(project_id: str, iid: int, request: Request) -> Dict[str, Any]:
        return await _get_issue(project_id, iid, request)

    @api.get("/projects/{namespace}/{project_name}/issues/{iid}")
    async def get_issue_ns(
        namespace: str, project_name: str, iid: int, request: Request
    ) -> Dict[str, Any]:
        return await _get_issue(f"{namespace}/{project_name}", iid, request)

    @api.put("/projects/{project_id}/issues/{iid}")
    async def update_issue_single(
        project_id: str,
        iid: int,
        request: Request,
        payload: Dict[str, Any] = Body(...),
    ) -> Dict[str, Any]:
        return await _update_issue(project_id, iid, request, payload)

    @api.put("/projects/{namespace}/{project_name}/issues/{iid}")
    async def update_issue_ns(
        namespace: str,
        project_name: str,
        iid: int,
        request: Request,
        payload: Dict[str, Any] = Body(...),
    ) -> Dict[str, Any]:
        return await _update_issue(f"{namespace}/{project_name}", iid, request, payload)

    @api.get("/projects/{project_id}/issues")
    async def list_issues_single(
        project_id: str,
        request: Request,
        state_filter: Optional[str] = Query(None, alias="state"),
        labels: Optional[str] = Query(None),
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
    ) -> JSONResponse:
        return await _list_issues(project_id, request, state_filter, labels, page, per_page)

    @api.get("/projects/{namespace}/{project_name}/issues")
    async def list_issues_ns(
        namespace: str,
        project_name: str,
        request: Request,
        state_filter: Optional[str] = Query(None, alias="state"),
        labels: Optional[str] = Query(None),
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
    ) -> JSONResponse:
        return await _list_issues(
            f"{namespace}/{project_name}", request, state_filter, labels, page, per_page
        )

    @api.post("/projects/{project_id}/issues")
    async def create_issue_single(
        project_id: str, request: Request, payload: Dict[str, Any] = Body(...)
    ) -> JSONResponse:
        return await _create_issue(project_id, request, payload)

    @api.post("/projects/{namespace}/{project_name}/issues")
    async def create_issue_ns(
        namespace: str,
        project_name: str,
        request: Request,
        payload: Dict[str, Any] = Body(...),
    ) -> JSONResponse:
        return await _create_issue(f"{namespace}/{project_name}", request, payload)

    @api.get("/projects/{project_id}/labels")
    async def list_labels_single(
        project_id: str,
        request: Request,
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
    ) -> JSONResponse:
        return await _list_labels(project_id, request, page, per_page)

    @api.get("/projects/{namespace}/{project_name}/labels")
    async def list_labels_ns(
        namespace: str,
        project_name: str,
        request: Request,
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
    ) -> JSONResponse:
        return await _list_labels(f"{namespace}/{project_name}", request, page, per_page)

    @api.get("/projects/{project_id:path}")
    async def get_project(project_id: str, request: Request) -> Dict[str, Any]:
        proj = _resolve_project(project_id)
        return _serialize_project(proj, request)

    app.include_router(api)

    # --- Control endpoints ---

    @app.post("/_control/emit-webhook")
    async def emit_webhook(body: EmitWebhookRequest, request: Request) -> JSONResponse:
        proj = state["projects"].get(body.project_id)
        if not proj:
            raise HTTPException(status_code=404, detail=f"Project {body.project_id} not found")

        base = _base_url(request)
        proj_payload = _serialize_project(proj, request)
        author = _get_or_create_user(body.author_username)
        now = _now_iso()
        event_uuid = body.event_uuid or str(uuid4())

        if body.kind == "issue":
            iid = body.issue_iid or _next_iid_for_project(proj["id"])
            existing = state["issues"].get((proj["id"], iid))
            if existing:
                issue_obj = existing
                if body.upsert_in_store:
                    issue_obj["title"] = body.title or issue_obj["title"]
                    if body.description is not None:
                        issue_obj["description"] = body.description
                    if body.labels:
                        issue_obj["labels"] = list(body.labels)
                    if body.action == "close":
                        issue_obj["state"] = "closed"
                        issue_obj["closed_at"] = now
                    elif body.action == "reopen":
                        issue_obj["state"] = "opened"
                        issue_obj["closed_at"] = None
                    issue_obj["updated_at"] = now
            else:
                state["next_gitlab_id"] += 1
                issue_obj = {
                    "id": state["next_gitlab_id"],
                    "iid": iid,
                    "project_id": proj["id"],
                    "title": body.title,
                    "description": body.description,
                    "state": "closed" if body.action == "close" else "opened",
                    "created_at": now,
                    "updated_at": now,
                    "closed_at": now if body.action == "close" else None,
                    "labels": list(body.labels),
                    "author": dict(author),
                    "upvotes": 0,
                    "downvotes": 0,
                    "user_notes_count": 0,
                }
                if body.upsert_in_store:
                    state["issues"][(proj["id"], iid)] = issue_obj
                    state["notes"].setdefault((proj["id"], iid), [])

            issue_url = f"{base}/{proj['path_with_namespace']}/-/issues/{iid}"
            event_header = "Issue Hook"
            payload: Dict[str, Any] = {
                "object_kind": "issue",
                "event_type": "issue",
                "user": _serialize_user(author, request),
                "project": proj_payload,
                "object_attributes": {
                    "id": issue_obj["id"],
                    "iid": iid,
                    "title": issue_obj["title"],
                    "description": issue_obj["description"],
                    "state": issue_obj["state"],
                    "action": body.action,
                    "created_at": issue_obj["created_at"],
                    "updated_at": issue_obj["updated_at"],
                    "url": issue_url,
                },
                "labels": [{"title": lbl} for lbl in issue_obj.get("labels", [])],
            }
        else:
            iid = body.issue_iid or 1
            issue_obj = state["issues"].get((proj["id"], iid))
            if not issue_obj:
                state["next_gitlab_id"] += 1
                issue_obj = {
                    "id": state["next_gitlab_id"],
                    "iid": iid,
                    "project_id": proj["id"],
                    "title": body.title,
                    "description": body.description,
                    "state": "opened",
                    "created_at": now,
                    "updated_at": now,
                    "closed_at": None,
                    "labels": list(body.labels),
                    "author": dict(_get_or_create_user("alice.dev")),
                    "upvotes": 0,
                    "downvotes": 0,
                    "user_notes_count": 0,
                }
                if body.upsert_in_store:
                    state["issues"][(proj["id"], iid)] = issue_obj
                    state["notes"].setdefault((proj["id"], iid), [])

            state["next_note_id"] += 1
            note_id = state["next_note_id"]
            note_obj = {
                "id": note_id,
                "body": body.note_body,
                "author": dict(author),
                "created_at": now,
                "updated_at": now,
                "system": False,
                "noteable_id": issue_obj["id"],
                "noteable_iid": iid,
                "noteable_type": "Issue",
            }
            if body.upsert_in_store:
                state["notes"].setdefault((proj["id"], iid), []).append(note_obj)
                issue_obj["user_notes_count"] = len(state["notes"][(proj["id"], iid)])
                issue_obj["updated_at"] = now

            issue_url = f"{base}/{proj['path_with_namespace']}/-/issues/{iid}"
            note_url = f"{issue_url}#note_{note_id}"
            event_header = "Note Hook"
            payload = {
                "object_kind": "note",
                "event_type": "note",
                "user": _serialize_user(author, request),
                "project": proj_payload,
                "issue": {
                    "id": issue_obj["id"],
                    "iid": iid,
                    "title": issue_obj["title"],
                    "description": issue_obj["description"],
                    "state": issue_obj["state"],
                    "created_at": issue_obj["created_at"],
                    "updated_at": issue_obj["updated_at"],
                    "url": issue_url,
                    "labels": [{"title": lbl} for lbl in issue_obj.get("labels", [])],
                },
                "object_attributes": {
                    "id": note_id,
                    "note": body.note_body,
                    "noteable_type": "Issue",
                    "noteable_id": issue_obj["id"],
                    "author_id": author["id"],
                    "created_at": now,
                    "updated_at": now,
                    "url": note_url,
                },
            }

        headers = {
            "Content-Type": "application/json",
            "X-Gitlab-Event": event_header,
            "X-Gitlab-Token": body.secret,
            "X-Gitlab-Event-UUID": event_uuid,
        }

        status_code: Optional[int] = None
        response_text: Optional[str] = None
        if body.deliver:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(body.target_url, json=payload, headers=headers)
                status_code = resp.status_code
                response_text = resp.text

        state["emitted_webhooks"].append(
            {
                "timestamp": now,
                "kind": body.kind,
                "target_url": body.target_url,
                "event_uuid": event_uuid,
                "status_code": status_code,
                "payload": payload,
            }
        )

        return JSONResponse(
            status_code=200,
            content={
                "status_code": status_code,
                "response": response_text,
                "event_uuid": event_uuid,
                "headers": headers,
                "payload": payload,
            },
        )

    @app.post("/_control/set-rate-limit")
    async def set_rate_limit(body: SetRateLimitRequest) -> Dict[str, int]:
        state["rate_limit"]["remaining_429"] = max(0, body.count)
        state["rate_limit"]["retry_after"] = max(0, body.retry_after)
        return dict(state["rate_limit"])

    @app.post("/_control/set-timeout")
    async def set_timeout(body: SetTimeoutRequest) -> Dict[str, int]:
        state["timeout"]["delay_ms"] = max(0, body.delay_ms)
        return dict(state["timeout"])

    @app.get("/_control/state")
    async def get_state() -> Dict[str, Any]:
        return {
            "projects": state["projects"],
            "issues": [
                {
                    "project_id": pid,
                    "iid": iid,
                    **issue,
                }
                for (pid, iid), issue in sorted(state["issues"].items())
            ],
            "notes": {
                f"{pid}:{iid}": note_list
                for (pid, iid), note_list in sorted(state["notes"].items())
            },
            "labels": state["labels"],
            "rate_limit": state["rate_limit"],
            "timeout": state["timeout"],
            "emitted_webhooks": state["emitted_webhooks"],
            "api_requests": state["api_requests"],
        }

    @app.post("/_control/reset")
    async def reset(body: Optional[ResetRequest] = None) -> Dict[str, Any]:
        seed = True if body is None else body.seed
        fresh = _build_initial_state(seed=seed)
        state.clear()
        state.update(fresh)
        return {"status": "reset", "seed": seed, "issue_count": len(state["issues"])}

    return app


app = create_app()
