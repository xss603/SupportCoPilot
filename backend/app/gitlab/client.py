from typing import List, Optional, Dict, Any
import gitlab
from app.core.config import settings


class GitLabManager:
    def __init__(self):
        self.url = settings.GITLAB_URL.rstrip("/")
        self.token = settings.effective_gitlab_write_token
        self.gl: Optional[gitlab.Gitlab] = None
        self._initialized = False

    def _ensure_client(self) -> Optional[gitlab.Gitlab]:
        if self._initialized:
            return self.gl
        self._initialized = True
        try:
            if self.token and not self.token.startswith("glpat-your-token"):
                self.gl = gitlab.Gitlab(
                    self.url,
                    private_token=self.token,
                    timeout=settings.GITLAB_TIMEOUT_SECONDS,
                )
                self.gl.auth()
                print(f"✅ Authenticated to GitLab at {self.url} as {self.gl.user.username}")
        except Exception as e:
            print(f"Notice: GitLab authentication skipped ({e}). Operating in simulation/offline mode.")
            self.gl = None
        return self.gl

    def add_comment(self, project_id: int, issue_iid: int, body: str) -> Dict[str, Any]:
        """Post a discussion note on a GitLab issue."""
        gl = self._ensure_client()
        if not gl:
            print(f"[Simulated GitLab API] Comment posted to Project {project_id} Issue #{issue_iid}: {body[:80]}...")
            return {"id": 999999, "body": body, "created_at": "simulated"}

        try:
            project = gl.projects.get(project_id)
            issue = project.issues.get(issue_iid)
            note = issue.notes.create({"body": body})
            return {"id": note.id, "body": note.body, "created_at": note.created_at}
        except Exception as e:
            print(f"GitLab API error adding comment: {e}")
            raise

    def update_labels(self, project_id: int, issue_iid: int, add_labels: List[str]) -> List[str]:
        """Add labels to an issue without overwriting existing labels."""
        gl = self._ensure_client()
        if not gl:
            print(f"[Simulated GitLab API] Labels added to Project {project_id} Issue #{issue_iid}: {add_labels}")
            return add_labels

        try:
            project = gl.projects.get(project_id)
            issue = project.issues.get(issue_iid)
            existing = issue.labels or []
            merged = list(set(existing + add_labels))
            issue.labels = merged
            issue.save()
            return merged
        except Exception as e:
            print(f"GitLab API error updating labels: {e}")
            raise

    def clone_or_escalate_issue(
        self,
        source_project_id: int,
        source_issue_iid: int,
        target_project_id: int,
        title: str,
        description: str,
        labels: List[str],
    ) -> Dict[str, Any]:
        """
        Creates a downstream / escalated ticket in a target repository with an automatic backlink.
        """
        backlink = f"\n\n---\n*Cloned/Escalated from Support Issue #{source_issue_iid} in Project {source_project_id}*"
        full_desc = description + backlink

        gl = self._ensure_client()
        if not gl:
            print(f"[Simulated GitLab API] Cloned issue to Target Project {target_project_id}: '{title}'")
            return {
                "id": 888888,
                "iid": 42,
                "project_id": target_project_id,
                "title": title,
                "web_url": f"{self.url}/project/{target_project_id}/issues/42",
            }

        try:
            target_project = gl.projects.get(target_project_id)
            new_issue = target_project.issues.create({
                "title": title,
                "description": full_desc,
                "labels": labels,
            })

            self.add_comment(
                source_project_id,
                source_issue_iid,
                f"🔗 **Downstream Ticket Created:** [{new_issue.title}]({new_issue.web_url}) in `{target_project.name}`",
            )

            return {
                "id": new_issue.id,
                "iid": new_issue.iid,
                "project_id": target_project_id,
                "title": new_issue.title,
                "web_url": new_issue.web_url,
            }
        except Exception as e:
            print(f"GitLab API error cloning issue: {e}")
            raise


gitlab_manager = GitLabManager()
