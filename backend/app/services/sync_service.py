from typing import Any, Dict, List, Optional
from sqlalchemy import select
from app.core.config import settings
from app.db.session import async_session_factory
from app.gitlab.client import gitlab_manager
from app.models.entities import Issue
from app.services.triage_service import triage_service


def fetch_new_gitlab_issues(project_id: str, limit: int = 50) -> Dict[str, Any]:
    gl = gitlab_manager._ensure_client()
    if not gl:
        raise RuntimeError("GitLab client unconfigured or authentication failed (check GITLAB_PRIVATE_TOKEN)")
    project = gl.projects.get(project_id)
    return {"project": project, "issues": project.issues.list(state="opened", per_page=limit)}


async def ingest_issues(project_id: str, limit: int = 50) -> Dict[str, Any]:
    """Pull open issues from GitLab, store unseen ones. Returns new issue ids to triage."""
    data = fetch_new_gitlab_issues(project_id, limit)
    project, gl_issues = data["project"], data["issues"]
    new_ids: List[str] = []
    async with async_session_factory() as db:
        for gi in gl_issues:
            res = await db.execute(select(Issue).where(Issue.project_id == project.id, Issue.iid == gi.iid))
            if res.scalar_one_or_none():
                continue
            issue = Issue(
                gitlab_id=gi.id, project_id=project.id, iid=gi.iid, title=gi.title,
                description=gi.description, state=gi.state,
                author_username=(gi.author or {}).get("username", "unknown"),
                author_name=(gi.author or {}).get("name"),
                labels=gi.labels or [], web_url=gi.web_url, status="ingested",
            )
            db.add(issue)
            await db.commit()
            await db.refresh(issue)
            new_ids.append(str(issue.id))
    return {"fetched": len(gl_issues), "new": len(new_ids), "new_issue_ids": new_ids}


async def triage_issues_by_id(issue_ids: List[str]) -> None:
    from uuid import UUID
    for iid in issue_ids:
        try:
            async with async_session_factory() as db:
                res = await db.execute(select(Issue).where(Issue.id == UUID(iid)))
                issue = res.scalar_one_or_none()
                if issue:
                    await triage_service.triage_issue(db, issue)
        except Exception as e:  # keep going on per-issue failures
            print(f"Triage failed for {iid}: {e}")
