"""Shared pytest fixtures for local mock servers, ASGI clients, and environment config."""

from __future__ import annotations

import os
from typing import Dict, Iterator

import httpx
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from tests.mocks.mock_docs import create_app as create_docs_app
from tests.mocks.mock_gitlab import create_app as create_gitlab_app
from tests.mocks.mock_llm import create_app as create_llm_app
from tests.mocks.mock_runner import MockCluster
from tests.mocks.mock_slack import create_app as create_slack_app


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def mock_cluster() -> Iterator[MockCluster]:
    with MockCluster(host="127.0.0.1") as cluster:
        yield cluster


@pytest.fixture
def reset_mocks(mock_cluster: MockCluster) -> Iterator[MockCluster]:
    mock_cluster.reset_all()
    yield mock_cluster
    mock_cluster.reset_all()


# --- In-process ASGI App & Client Fixtures (zero TCP overhead) ---


@pytest.fixture
def gitlab_mock_app() -> FastAPI:
    return create_gitlab_app()


@pytest.fixture
def llm_mock_app() -> FastAPI:
    return create_llm_app()


@pytest.fixture
def docs_mock_app() -> FastAPI:
    return create_docs_app()


@pytest.fixture
def slack_mock_app() -> FastAPI:
    return create_slack_app()


@pytest.fixture
def gitlab_asgi_client(gitlab_mock_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(gitlab_mock_app) as client:
        yield client


@pytest.fixture
def llm_asgi_client(llm_mock_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(llm_mock_app) as client:
        yield client


@pytest.fixture
def docs_asgi_client(docs_mock_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(docs_mock_app) as client:
        yield client


@pytest.fixture
def slack_asgi_client(slack_mock_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(slack_mock_app) as client:
        yield client


def make_async_asgi_client(app: FastAPI, base_url: str = "http://testserver") -> httpx.AsyncClient:
    """Helper returning an httpx.AsyncClient bound directly to a FastAPI app via ASGITransport."""
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=base_url)


# --- Live HTTP Client Fixtures pointing at MockCluster ---


@pytest.fixture
def gitlab_http_client(reset_mocks: MockCluster) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=reset_mocks.gitlab_url, timeout=10.0) as client:
        yield client


@pytest.fixture
def llm_http_client(reset_mocks: MockCluster) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=reset_mocks.llm_url, timeout=10.0) as client:
        yield client


@pytest.fixture
def docs_http_client(reset_mocks: MockCluster) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=reset_mocks.docs_url, timeout=10.0) as client:
        yield client


@pytest.fixture
def slack_http_client(reset_mocks: MockCluster) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=reset_mocks.slack_url, timeout=10.0) as client:
        yield client


# --- Environment Configuration Fixture ---


@pytest.fixture
def mock_env(
    reset_mocks: MockCluster,
    monkeypatch: pytest.MonkeyPatch,
) -> Dict[str, str]:
    backend_url = os.getenv("TEST_BACKEND_URL", "http://127.0.0.1:8000")
    env_vars = {
        "GITLAB_URL": reset_mocks.gitlab_url,
        "GITLAB_READ_TOKEN": "glpat-mock-read-token",
        "GITLAB_WRITE_TOKEN": "glpat-mock-write-token",
        "GITLAB_PRIVATE_TOKEN": "glpat-mock-private-token",
        "GITLAB_WEBHOOK_SECRET": "mock-webhook-secret-xyz",
        "GITLAB_BOT_USERNAME": "platform-support-bot",
        "GITLAB_DEFAULT_PROJECT_ID": "101",
        "LLM_BASE_URL": f"{reset_mocks.llm_url}/v1",
        "LLM_API_KEY": "sk-mock-llm-key",
        "DOCS_BASE_URL": reset_mocks.docs_url,
        "ACADEMY_BASE_URL": f"{reset_mocks.docs_url}/academy",
        "CRAWLER_ALLOWED_DOMAINS": "127.0.0.1,localhost",
        "SLACK_WEBHOOK_URL": f"{reset_mocks.slack_url}/webhook",
        "MATTERMOST_WEBHOOK_URL": f"{reset_mocks.slack_url}/webhook",
        "BACKEND_BASE_URL": backend_url,
    }
    for key, val in env_vars.items():
        monkeypatch.setenv(key, val)
    return env_vars
