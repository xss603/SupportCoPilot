import asyncio
from unittest.mock import MagicMock
import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import create_async_engine
from starlette.requests import Request

from app.api.endpoints.webhooks import gitlab_webhook_listener
from app.core.config import Settings, settings


def test_settings_parses_csv_and_strips_wildcard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRAWLER_ALLOWED_DOMAINS", "docs.corp.io,academy.corp.io")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,*")
    s = Settings(_env_file=None)
    assert s.CRAWLER_ALLOWED_DOMAINS == ["docs.corp.io", "academy.corp.io"]
    assert s.CORS_ORIGINS == ["http://localhost:5173"]


def test_settings_parses_empty_and_star_only_as_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "*")
    monkeypatch.setenv("CRAWLER_ALLOWED_DOMAINS", "")
    s = Settings(_env_file=None)
    assert s.CORS_ORIGINS == []
    assert s.CRAWLER_ALLOWED_DOMAINS == []

    monkeypatch.setenv("CORS_ORIGINS", "   ")
    s2 = Settings(_env_file=None)
    assert s2.CORS_ORIGINS == []


def test_settings_parses_json_array_and_strips_wildcard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:5173", "*"]')
    monkeypatch.setenv("CRAWLER_ALLOWED_DOMAINS", '["docs.corp.io", "academy.corp.io"]')
    s = Settings(_env_file=None)
    assert s.CORS_ORIGINS == ["http://localhost:5173"]
    assert s.CRAWLER_ALLOWED_DOMAINS == ["docs.corp.io", "academy.corp.io"]


@pytest.mark.parametrize(
    "raw_dsn",
    [
        "postgresql://u:p@h:5432/db",
        "postgres://u:p@h:5432/db",
    ],
)
def test_settings_normalizes_plain_postgres_dsn_to_asyncpg(
    monkeypatch: pytest.MonkeyPatch, raw_dsn: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", raw_dsn)
    s = Settings(_env_file=None)
    assert s.DATABASE_URL == "postgresql+asyncpg://u:p@h:5432/db"
    assert s.DATABASE_URL_SYNC == "postgresql+psycopg2://u:p@h:5432/db"
    engine = create_async_engine(s.DATABASE_URL)
    assert engine.driver == "asyncpg"


def test_webhook_rejects_non_ascii_token_with_401(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "GITLAB_WEBHOOK_SECRET", "super-secret-token")
    monkeypatch.setattr(settings, "DEBUG", False)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/webhooks/gitlab",
        "headers": [],
    }
    request = Request(scope)
    bg = BackgroundTasks()
    fake_db = MagicMock()

    async def _call():
        await gitlab_webhook_listener(
            request=request,
            background_tasks=bg,
            x_gitlab_token="tökén-ütf8-🚀",
            x_gitlab_event="Issue Hook",
            x_gitlab_event_uuid="evt-1",
            db=fake_db,
        )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_call())

    assert exc_info.value.status_code == 401
