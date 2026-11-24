"""Mock Slack / Mattermost Incoming Webhook receiver for SLA alert tests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import Body, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ToggleErrorRequest(BaseModel):
    enabled: Optional[bool] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_app() -> FastAPI:
    app = FastAPI(title="Mock Slack/Mattermost Webhook", version="1.0.0")
    state: Dict[str, Any] = {
        "error_mode": False,
        "alerts": [],
    }

    @app.get("/healthz")
    async def healthz() -> Dict[str, str]:
        return {"status": "ok", "service": "mock_slack"}

    @app.post("/webhook")
    async def receive_webhook(
        request: Request,
        payload: Dict[str, Any] = Body(default_factory=dict),
    ) -> JSONResponse:
        if state["error_mode"]:
            return JSONResponse(
                status_code=500,
                content={"ok": False, "error": "simulated_slack_outage"},
            )

        record = {
            "id": str(uuid4()),
            "received_at": _now_iso(),
            "headers": {
                "content-type": request.headers.get("content-type", ""),
                "user-agent": request.headers.get("user-agent", ""),
            },
            "payload": payload,
        }
        state["alerts"].append(record)
        return JSONResponse(status_code=200, content={"ok": True})

    @app.get("/_alerts")
    async def list_alerts() -> Dict[str, Any]:
        alerts: List[Dict[str, Any]] = state["alerts"]
        return {"count": len(alerts), "alerts": list(alerts)}

    @app.post("/_control/toggle-error")
    async def toggle_error(body: Optional[ToggleErrorRequest] = None) -> Dict[str, bool]:
        if body is not None and body.enabled is not None:
            state["error_mode"] = body.enabled
        else:
            state["error_mode"] = not state["error_mode"]
        return {"error_mode": bool(state["error_mode"])}

    @app.post("/_control/reset")
    async def reset() -> Dict[str, Any]:
        state["error_mode"] = False
        state["alerts"].clear()
        return {"status": "reset", "error_mode": False, "count": 0}

    return app


app = create_app()
