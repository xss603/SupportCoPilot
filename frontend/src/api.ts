import {
  ActionExecutionResponse,
  ApproveActionRequest,
  ApproveActionsResponse,
  AuditLogEntry,
  AuthUser,
  CloneIssueRequest,
  CloneIssueResponse,
  CrawlerSourceType,
  CrawlerSyncRun,
  CrawlTriggerResponse,
  DashboardStats,
  DocChunkItem,
  DocDraftResponse,
  DocsDriftCluster,
  GoldenExample,
  IssueDetail,
  IssueListItem,
  LoginRequest,
  LoginResponse,
  MessageResponse,
  PlatformRulesConfig,
  RAGPlaygroundResponse,
  RejectTriageResponse,
  ReTriageResponse,
  SLAStatus,
} from './types';

const API_BASE = '/api/v1';
const TOKEN_STORAGE_KEY = 'gitlab_support_auth_token';

let inMemoryToken: string | null = null;

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export function getAuthToken(): string | null {
  if (inMemoryToken) return inMemoryToken;
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage.getItem(TOKEN_STORAGE_KEY);
    }
  } catch {
    // Ignore storage access failures in restricted environments
  }
  return null;
}

export function setAuthToken(token: string): void {
  inMemoryToken = token;
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
    }
  } catch {
    // Ignore storage access failures
  }
}

export function clearAuthToken(): void {
  inMemoryToken = null;
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch {
    // Ignore storage access failures
  }
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers || {});
  const token = getAuthToken();
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  if (init.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: init.credentials ?? 'include',
    headers,
  });

  if (!res.ok) {
    let detail: unknown = undefined;
    let message = `Request failed (${res.status})`;
    try {
      const parsed = await res.json();
      detail = parsed;
      if (parsed && typeof parsed.detail === 'string') {
        message = parsed.detail;
      }
    } catch {
      // Non-JSON error body
    }
    throw new ApiError(res.status, message, detail);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

// --- Auth & RBAC ---

export async function login(payload: LoginRequest): Promise<LoginResponse> {
  const data = await apiFetch<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  setAuthToken(data.access_token);
  return data;
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  return apiFetch<AuthUser>('/auth/me');
}

// --- Issues & Actions ---

export interface FetchIssuesParams {
  status?: string;
  category?: string;
  priority?: string;
  sla_status?: SLAStatus;
  search?: string;
  limit?: number;
  offset?: number;
}

export async function fetchIssues(params?: FetchIssuesParams): Promise<IssueListItem[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.category) query.set('category', params.category);
  if (params?.priority) query.set('priority', params.priority);
  if (params?.sla_status) query.set('sla_status', params.sla_status);
  if (params?.search) query.set('search', params.search);
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  if (params?.offset !== undefined) query.set('offset', String(params.offset));

  const qs = query.toString();
  return apiFetch<IssueListItem[]>(qs ? `/issues?${qs}` : '/issues');
}

export async function fetchIssueDetail(id: string): Promise<IssueDetail> {
  return apiFetch<IssueDetail>(`/issues/${id}`);
}

export async function approveActions(
  issueId: string,
  payload?: ApproveActionRequest
): Promise<ApproveActionsResponse> {
  return apiFetch<ApproveActionsResponse>(`/issues/${issueId}/approve`, {
    method: 'POST',
    body: JSON.stringify(payload || {}),
  });
}

export async function rejectTriage(
  issueId: string,
  reason?: string
): Promise<RejectTriageResponse> {
  return apiFetch<RejectTriageResponse>(`/issues/${issueId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

export async function cloneIssue(
  issueId: string,
  payload: CloneIssueRequest
): Promise<CloneIssueResponse> {
  return apiFetch<CloneIssueResponse>(`/issues/${issueId}/clone`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function reTriageIssue(issueId: string): Promise<ReTriageResponse> {
  return apiFetch<ReTriageResponse>(`/issues/${issueId}/re-triage`, {
    method: 'POST',
  });
}

export interface SyncResponse {
  project_id: string;
  fetched: number;
  new: number;
  status: string;
}

export async function syncIssues(projectId?: string): Promise<SyncResponse> {
  const qs = projectId ? `?project_id=${encodeURIComponent(projectId)}` : '';
  return apiFetch<SyncResponse>(`/issues/sync${qs}`, { method: 'POST' });
}

export async function retryAction(actionId: string): Promise<ActionExecutionResponse> {
  return apiFetch<ActionExecutionResponse>(`/actions/${actionId}/retry`, {
    method: 'POST',
  });
}

// --- Knowledge Base, Crawler & Docs Drift ---

export async function fetchKnowledgeChunks(params?: {
  source_type?: string;
  limit?: number;
  offset?: number;
}): Promise<DocChunkItem[]> {
  const query = new URLSearchParams();
  if (params?.source_type) query.set('source_type', params.source_type);
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  if (params?.offset !== undefined) query.set('offset', String(params.offset));
  const qs = query.toString();
  return apiFetch<DocChunkItem[]>(qs ? `/knowledge/chunks?${qs}` : '/knowledge/chunks');
}

export async function triggerCrawl(
  source_type: CrawlerSourceType,
  url?: string
): Promise<CrawlTriggerResponse> {
  return apiFetch<CrawlTriggerResponse>('/knowledge/crawl', {
    method: 'POST',
    body: JSON.stringify({ source_type, url }),
  });
}

export async function fetchCrawlStatus(limit = 20): Promise<CrawlerSyncRun[]> {
  return apiFetch<CrawlerSyncRun[]>(`/knowledge/crawl/status?limit=${limit}`);
}

export async function queryRAGPlayground(
  query: string,
  top_k = 4,
  source_type?: string
): Promise<RAGPlaygroundResponse> {
  return apiFetch<RAGPlaygroundResponse>('/knowledge/playground', {
    method: 'POST',
    body: JSON.stringify({ query, top_k, source_type }),
  });
}

export async function fetchDocsDriftClusters(statusFilter?: string): Promise<DocsDriftCluster[]> {
  const qs = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : '';
  return apiFetch<DocsDriftCluster[]>(`/knowledge/drift${qs}`);
}

export async function generateDocDraft(clusterId: string): Promise<DocDraftResponse> {
  return apiFetch<DocDraftResponse>(`/knowledge/drift/${clusterId}/generate-draft`, {
    method: 'POST',
  });
}

// --- Rules, Feedback, Audit & Stats ---

export async function fetchRules(): Promise<PlatformRulesConfig> {
  return apiFetch<PlatformRulesConfig>('/rules');
}

export async function updateRules(payload: PlatformRulesConfig): Promise<PlatformRulesConfig> {
  return apiFetch<PlatformRulesConfig>('/rules', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function fetchGoldenExamples(params?: {
  category?: string;
  limit?: number;
  offset?: number;
}): Promise<GoldenExample[]> {
  const query = new URLSearchParams();
  if (params?.category) query.set('category', params.category);
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  if (params?.offset !== undefined) query.set('offset', String(params.offset));
  const qs = query.toString();
  return apiFetch<GoldenExample[]>(qs ? `/feedback/golden-examples?${qs}` : '/feedback/golden-examples');
}

export async function deleteGoldenExample(exampleId: string): Promise<MessageResponse> {
  return apiFetch<MessageResponse>(`/feedback/golden-examples/${exampleId}`, {
    method: 'DELETE',
  });
}

export async function fetchAuditLogs(params?: {
  entity_type?: string;
  event?: string;
  actor?: string;
  limit?: number;
  offset?: number;
}): Promise<AuditLogEntry[]> {
  const query = new URLSearchParams();
  if (params?.entity_type) query.set('entity_type', params.entity_type);
  if (params?.event) query.set('event', params.event);
  if (params?.actor) query.set('actor', params.actor);
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  if (params?.offset !== undefined) query.set('offset', String(params.offset));
  const qs = query.toString();
  return apiFetch<AuditLogEntry[]>(qs ? `/audit-logs?${qs}` : '/audit-logs');
}

export async function fetchStats(): Promise<DashboardStats> {
  return apiFetch<DashboardStats>('/stats');
}

/**
 * Builds the authenticated SSE stream URL for `/api/v1/stats/events`.
 *
 * Auth contract (`docs/THREAT_MODEL.md` § T5):
 * - Native browser `EventSource` cannot send custom `Authorization` headers;
 *   open with `new EventSource(getStatsEventsUrl(cursor), { withCredentials: true })`
 *   so the browser sends the `HttpOnly; SameSite=Lax; Path=/api/v1` cookie issued
 *   by `POST /api/v1/auth/login` (or use `fetch()` streaming with `Authorization: Bearer`).
 * - Never append `?token=` query parameters to this URL.
 */
export function getStatsEventsUrl(cursor?: string): string {
  if (!cursor) return `${API_BASE}/stats/events`;
  return `${API_BASE}/stats/events?cursor=${encodeURIComponent(cursor)}`;
}
