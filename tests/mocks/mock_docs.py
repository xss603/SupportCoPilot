"""Mock Docs & Academy Portal HTTP server for offline RAG crawling & SSRF tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from xml.sax.saxutils import escape

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"

DOCS_SLUGS = (
    "istio-502",
    "vault-pki",
    "db-migrations",
    "k8s-troubleshooting",
    "ci-runners",
)

ACADEMY_ROUTES: Dict[str, tuple[str, str]] = {
    "istio-mtls-deep-dive": ("academy-istio-mtls.html", "text/html"),
    "postgres-migrations": ("academy-postgres-migrations.md", "text/markdown"),
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_app() -> FastAPI:
    app = FastAPI(title="Mock Docs & Academy Portal", version="1.0.0")
    requests_log: List[Dict[str, Any]] = []

    def _record(request: Request, note: str = "") -> None:
        requests_log.append(
            {
                "timestamp": _now_iso(),
                "method": request.method,
                "path": request.url.path,
                "user_agent": request.headers.get("user-agent", ""),
                "note": note,
            }
        )

    @app.get("/healthz")
    async def healthz() -> Dict[str, str]:
        return {"status": "ok", "service": "mock_docs"}

    @app.get("/", response_class=HTMLResponse)
    @app.get("/index.html", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        _record(request)
        html = (CORPUS_DIR / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(content=html)

    @app.get("/sitemap.xml")
    async def sitemap(request: Request) -> Response:
        _record(request)
        base = str(request.base_url).rstrip("/")
        urls = [
            f"{base}/",
            *[f"{base}/docs/{slug}" for slug in DOCS_SLUGS],
            *[f"{base}/docs/{slug}.md" for slug in DOCS_SLUGS],
            *[f"{base}/academy/{slug}" for slug in ACADEMY_ROUTES],
        ]
        entries = "\n".join(
            f"  <url><loc>{escape(u)}</loc><changefreq>weekly</changefreq></url>"
            for u in urls
        )
        xml_body = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{entries}\n"
            "</urlset>\n"
        )
        return Response(content=xml_body, media_type="application/xml")

    @app.get("/docs/{slug}")
    async def get_doc(slug: str, request: Request) -> Response:
        _record(request)
        if slug.endswith(".md"):
            clean_slug = slug[:-3]
            if clean_slug not in DOCS_SLUGS:
                raise HTTPException(status_code=404, detail="Doc markdown not found")
            content = (CORPUS_DIR / f"{clean_slug}.md").read_text(encoding="utf-8")
            return PlainTextResponse(content=content, media_type="text/markdown; charset=utf-8")

        clean_slug = slug[:-5] if slug.endswith(".html") else slug
        if clean_slug not in DOCS_SLUGS:
            raise HTTPException(status_code=404, detail="Doc page not found")
        content = (CORPUS_DIR / f"{clean_slug}.html").read_text(encoding="utf-8")
        return HTMLResponse(content=content)

    @app.get("/academy/{slug}")
    async def get_academy(slug: str, request: Request) -> Response:
        _record(request)
        clean_slug = slug
        for suffix in (".html", ".md"):
            if clean_slug.endswith(suffix):
                clean_slug = clean_slug[: -len(suffix)]
                break

        if clean_slug not in ACADEMY_ROUTES:
            raise HTTPException(status_code=404, detail="Academy guide not found")

        filename, media_type = ACADEMY_ROUTES[clean_slug]
        content = (CORPUS_DIR / filename).read_text(encoding="utf-8")
        if media_type == "text/html":
            return HTMLResponse(content=content)
        return PlainTextResponse(content=content, media_type="text/markdown; charset=utf-8")

    @app.get("/ssrf-trap")
    async def ssrf_trap(request: Request) -> Response:
        _record(request, note="ssrf-trap-metadata")
        return Response(
            status_code=302,
            headers={
                "Location": "http://169.254.169.254/latest/meta-data/iam/security-credentials/"
            },
        )

    @app.get("/ssrf-trap-loopback")
    async def ssrf_trap_loopback(request: Request) -> Response:
        _record(request, note="ssrf-trap-loopback")
        return Response(
            status_code=302,
            headers={"Location": "http://127.0.0.1:8000/healthz"},
        )

    @app.get("/_control/requests")
    async def get_requests() -> Dict[str, Any]:
        return {"count": len(requests_log), "requests": list(requests_log)}

    @app.post("/_control/reset")
    async def reset() -> Dict[str, str]:
        requests_log.clear()
        return {"status": "reset"}

    return app


app = create_app()
