import { config } from '../config.js';

export interface GitLabIssue {
  id: number;
  iid: number;
  project_id: number;
  title: string;
  description: string;
  state: string;
  labels: string[];
  author: {
    id: number;
    username: string;
    name: string;
  };
  web_url: string;
  created_at: string;
}

export interface GitLabDiscussionNote {
  id: number;
  body: string;
  author: {
    username: string;
  };
  system: boolean;
  created_at: string;
}

export class GitLabClient {
  private baseUrl: string;
  private token: string;

  constructor() {
    this.baseUrl = config.GITLAB_URL.replace(/\/+$/, '');
    this.token = config.GITLAB_TOKEN;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}/api/v4${path}`;
    const headers = {
      'PRIVATE-TOKEN': this.token,
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...(options.headers || {}),
    };

    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`GitLab API error [${res.status} ${res.statusText}] at ${path}: ${errText}`);
    }

    return (await res.json()) as T;
  }

  /**
   * List open issues for a project, optionally filtering by untriaged status
   */
  async listOpenIssues(projectId: string | number): Promise<GitLabIssue[]> {
    const encodedId = encodeURIComponent(String(projectId));
    return this.request<GitLabIssue[]>(`/projects/${encodedId}/issues?state=opened&per_page=50`);
  }

  /**
   * Fetch single issue details
   */
  async getIssue(projectId: string | number, issueIid: number): Promise<GitLabIssue> {
    const encodedId = encodeURIComponent(String(projectId));
    return this.request<GitLabIssue>(`/projects/${encodedId}/issues/${issueIid}`);
  }

  /**
   * Get notes/comments on an issue
   */
  async listIssueNotes(projectId: string | number, issueIid: number): Promise<GitLabDiscussionNote[]> {
    const encodedId = encodeURIComponent(String(projectId));
    return this.request<GitLabDiscussionNote[]>(`/projects/${encodedId}/issues/${issueIid}/notes?per_page=50`);
  }

  /**
   * Post a markdown note/comment on an issue
   */
  async createIssueNote(projectId: string | number, issueIid: number, body: string): Promise<GitLabDiscussionNote> {
    const encodedId = encodeURIComponent(String(projectId));
    return this.request<GitLabDiscussionNote>(`/projects/${encodedId}/issues/${issueIid}/notes`, {
      method: 'POST',
      body: JSON.stringify({ body }),
    });
  }

  /**
   * Update issue labels (adding labels without overwriting existing ones)
   */
  async addLabels(projectId: string | number, issueIid: number, newLabels: string[]): Promise<GitLabIssue> {
    const current = await this.getIssue(projectId, issueIid);
    const existing = current.labels || [];
    const merged = Array.from(new Set([...existing, ...newLabels]));

    const encodedId = encodeURIComponent(String(projectId));
    return this.request<GitLabIssue>(`/projects/${encodedId}/issues/${issueIid}`, {
      method: 'PUT',
      body: JSON.stringify({
        labels: merged.join(','),
      }),
    });
  }

  /**
   * Check if an issue has already been triaged
   */
  hasBeenTriaged(issue: GitLabIssue): boolean {
    const labels = issue.labels || [];
    return labels.some(l => l.toLowerCase() === 'ai-triaged');
  }
}

export const gitlab = new GitLabClient();
