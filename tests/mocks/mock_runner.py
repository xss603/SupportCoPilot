"""Unified socket-bound uvicorn launcher and CLI for the 4 local mock servers."""

from __future__ import annotations

import argparse
import json
import signal
import socket
import sys
import threading
import time
from typing import Any, Dict, Optional

import httpx
import uvicorn
from fastapi import FastAPI

from tests.mocks.mock_docs import create_app as create_docs_app
from tests.mocks.mock_gitlab import create_app as create_gitlab_app
from tests.mocks.mock_llm import create_app as create_llm_app
from tests.mocks.mock_slack import create_app as create_slack_app


class _ThreadSafeUvicornServer(uvicorn.Server):
    """Uvicorn server subclass that skips signal handler registration in worker threads."""

    def install_signal_handlers(self) -> None:  # pragma: no cover - trivial override
        return


class ManagedMockServer:
    """Runs a FastAPI app on a pre-bound TCP socket in a background daemon thread."""

    def __init__(
        self,
        name: str,
        app: FastAPI,
        host: str = "127.0.0.1",
        port: int = 0,
    ) -> None:
        self.name = name
        self.app = app
        self.host = host
        self.requested_port = port
        self.port: int = 0
        self._sock: Optional[socket.socket] = None
        self._server: Optional[_ThreadSafeUvicornServer] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def url(self) -> str:
        if not self.port:
            raise RuntimeError(f"Mock server '{self.name}' is not started")
        return f"http://{self.host}:{self.port}"

    def start(self, timeout_seconds: float = 5.0) -> "ManagedMockServer":
        if self._thread is not None and self._thread.is_alive():
            return self

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.requested_port))
        sock.listen(128)
        sock.setblocking(False)
        actual_port = sock.getsockname()[1]

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=actual_port,
            log_level="warning",
            access_log=False,
        )
        server = _ThreadSafeUvicornServer(config)

        self._sock = sock
        self.port = actual_port
        self._server = server
        self._thread = threading.Thread(
            target=server.run,
            kwargs={"sockets": [sock]},
            name=f"mock-{self.name}-{actual_port}",
            daemon=True,
        )
        self._thread.start()

        deadline = time.monotonic() + timeout_seconds
        last_err: Optional[Exception] = None
        health_url = f"{self.url}/healthz"
        with httpx.Client(timeout=1.0) as client:
            while time.monotonic() < deadline:
                if not self._thread.is_alive():
                    raise RuntimeError(f"Mock server '{self.name}' exited prematurely")
                try:
                    resp = client.get(health_url)
                    if resp.status_code == 200:
                        return self
                except Exception as exc:  # pragma: no cover - startup poll retry
                    last_err = exc
                time.sleep(0.025)

        self.stop()
        raise TimeoutError(
            f"Mock server '{self.name}' failed to become healthy at {health_url}: {last_err}"
        )

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
        self._thread = None
        self._server = None
        self._sock = None
        self.port = 0


class MockCluster:
    """Manages all 4 local mock servers (gitlab, llm, docs, slack) as a cohesive cluster."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        gitlab_port: int = 0,
        llm_port: int = 0,
        docs_port: int = 0,
        slack_port: int = 0,
    ) -> None:
        self.host = host
        self.docs = ManagedMockServer("docs", create_docs_app(), host=host, port=docs_port)
        self.slack = ManagedMockServer("slack", create_slack_app(), host=host, port=slack_port)
        self.gitlab = ManagedMockServer("gitlab", create_gitlab_app(), host=host, port=gitlab_port)
        self.llm = ManagedMockServer("llm", create_llm_app(), host=host, port=llm_port)
        self._started = False

    @property
    def gitlab_url(self) -> str:
        return self.gitlab.url

    @property
    def llm_url(self) -> str:
        return self.llm.url

    @property
    def docs_url(self) -> str:
        return self.docs.url

    @property
    def slack_url(self) -> str:
        return self.slack.url

    def urls_dict(self) -> Dict[str, str]:
        return {
            "gitlab_url": self.gitlab_url,
            "llm_url": self.llm_url,
            "docs_url": self.docs_url,
            "slack_url": self.slack_url,
        }

    def start(self) -> "MockCluster":
        if self._started:
            return self
        try:
            self.docs.start()
            self.slack.start()
            self.gitlab.start()
            self.llm.start()
            # Wire mock_llm's docs_base_url to the live mock_docs URL
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(
                    f"{self.llm.url}/_control/set-mode",
                    json={"mode": "normal", "docs_base_url": self.docs.url},
                )
                resp.raise_for_status()
            self._started = True
            return self
        except Exception:
            self.stop()
            raise

    def reset_all(self) -> None:
        with httpx.Client(timeout=5.0) as client:
            for srv in (self.gitlab, self.llm, self.docs, self.slack):
                resp = client.post(f"{srv.url}/_control/reset")
                resp.raise_for_status()
            # Re-ensure docs_base_url remains wired to active mock_docs
            client.post(
                f"{self.llm.url}/_control/set-mode",
                json={"mode": "normal", "docs_base_url": self.docs.url},
            ).raise_for_status()

    def stop(self) -> None:
        for srv in (self.llm, self.gitlab, self.slack, self.docs):
            srv.stop()
        self._started = False

    def __enter__(self) -> "MockCluster":
        return self.start()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run local mock servers for QA & E2E testing.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--gitlab-port", type=int, default=9001, help="Mock GitLab port (0=ephemeral)")
    parser.add_argument("--llm-port", type=int, default=9002, help="Mock LLM port (0=ephemeral)")
    parser.add_argument("--docs-port", type=int, default=9003, help="Mock Docs port (0=ephemeral)")
    parser.add_argument("--slack-port", type=int, default=9004, help="Mock Slack port (0=ephemeral)")
    args = parser.parse_args(argv)

    stop_event = threading.Event()

    def _handle_signal(_signum: int, _frame: Any) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    with MockCluster(
        host=args.host,
        gitlab_port=args.gitlab_port,
        llm_port=args.llm_port,
        docs_port=args.docs_port,
        slack_port=args.slack_port,
    ) as cluster:
        print(json.dumps(cluster.urls_dict(), indent=2), flush=True)
        while not stop_event.is_set():
            stop_event.wait(timeout=0.5)

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
