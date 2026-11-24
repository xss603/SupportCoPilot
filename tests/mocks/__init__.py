"""Local deterministic mock and stub servers for offline QA & E2E testing."""

from __future__ import annotations

from typing import Any

__all__ = [
    "create_gitlab_app",
    "create_llm_app",
    "create_docs_app",
    "create_slack_app",
    "ManagedMockServer",
    "MockCluster",
]


def __getattr__(name: str) -> Any:
    if name == "create_gitlab_app":
        from tests.mocks.mock_gitlab import create_app

        return create_app
    if name == "create_llm_app":
        from tests.mocks.mock_llm import create_app

        return create_app
    if name == "create_docs_app":
        from tests.mocks.mock_docs import create_app

        return create_app
    if name == "create_slack_app":
        from tests.mocks.mock_slack import create_app

        return create_app
    if name in {"ManagedMockServer", "MockCluster"}:
        from tests.mocks import mock_runner

        return getattr(mock_runner, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
