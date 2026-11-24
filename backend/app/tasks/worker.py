import asyncio
from typing import Any, Dict
from arq import cron
from sqlalchemy import select
from app.core.config import settings
from app.db.session import async_session_factory
from app.models.entities import Issue
from app.services.triage_service import triage_service
from app.gitlab.client import gitlab_manager


async def process_issue_task(ctx: Dict[Any, Any], issue_id_str: str) -> str:
    """Async ARQ task to process a single issue."""
    from uuid import UUID
    issue_id = UUID(issue_id_str)
    async with async_session_factory() as db:
        stmt = select(Issue).where(Issue.id == issue_id)
        res = await db.execute(stmt)
        issue = res.scalar_one_or_none()
        if not issue:
            return f"Issue {issue_id_str} not found"

        await triage_service.triage_issue(db, issue)
        return f"Successfully triaged Issue #{issue.iid}"


async def reconcile_gitlab_issues_task(ctx: Dict[Any, Any]) -> str:
    """Scheduled reconciliation task: polls GitLab for untriaged issues."""
    print("⏱️ [Reconciliation Poller] Checking for untriaged issues...")
    project_id = settings.GITLAB_DEFAULT_PROJECT_ID
    if not project_id or not gitlab_manager.gl:
        return "Reconciliation skipped: No default project or client unconfigured"

    try:
        project = gitlab_manager.gl.projects.get(project_id)
        issues = project.issues.list(state="opened", per_page=20)
        
        async with async_session_factory() as db:
            count = 0
            for gl_issue in issues:
                labels = gl_issue.labels or []
                if "ai-triaged" in labels:
                    continue

                # Check if already in DB
                stmt = select(Issue).where(Issue.project_id == project.id, Issue.iid == gl_issue.iid)
                res = await db.execute(stmt)
                existing = res.scalar_one_or_none()

                if not existing:
                    new_issue = Issue(
                        gitlab_id=gl_issue.id,
                        project_id=project.id,
                        iid=gl_issue.iid,
                        title=gl_issue.title,
                        description=gl_issue.description,
                        state=gl_issue.state,
                        author_username=gl_issue.author.get("username", "unknown"),
                        labels=labels,
                        web_url=gl_issue.web_url,
                        status="ingested"
                    )
                    db.add(new_issue)
                    await db.commit()
                    await db.refresh(new_issue)
                    await triage_service.triage_issue(db, new_issue)
                    count += 1

            return f"Reconciliation completed: {count} issues triaged"
    except Exception as e:
        print(f"Reconciliation error: {e}")
        return f"Error: {e}"


class WorkerSettings:
    functions = [process_issue_task]
    cron_jobs = [cron(reconcile_gitlab_issues_task, minute={0, 15, 30, 45})]
    redis_settings = settings.REDIS_URL
