export type UserRole = 'reviewer' | 'admin';

export type IssueStatus =
  | 'ingested'
  | 'triaging'
  | 'triaged'
  | 'auto_resolved'
  | 'pending_approval'
  | 'human_review'
  | 'closed';

export type PriorityLevel = 'P1' | 'P2' | 'P3' | 'P4';

export type IssueCategory =
  | 'bug'
  | 'feature_request'
  | 'configuration'
  | 'access_iam'
  | 'outage'
  | 'other';

export type ProposedActionType =
  | 'comment'
  | 'add_labels'
  | 'clone_issue'
  | 'escalate_downstream'
  | 'close_issue';

export type ProposedActionStatus =
  | 'DRAFT'
  | 'APPROVED'
  | 'EXECUTED'
  | 'FAILED'
  | 'REJECTED';

export type ApprovalStatus =
  | 'pending'
  | 'approved'
  | 'rejected'
  | 'auto_executed';

export type SLAStatus = 'ok' | 'at_risk' | 'breached';

export type CrawlerSourceType = 'runbooks' | 'documentation' | 'academy';

export interface AuthUser {
  id: string;
  username: string;
  email?: string | null;
  full_name?: string | null;
  role: UserRole;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export interface MessageResponse {
  status: string;
  message: string;
}

export interface SLACountdown {
  priority: PriorityLevel;
  target_minutes: number;
  due_at: string;
  remaining_seconds: number;
  status: SLAStatus;
  alert_sent: boolean;
}

export interface CitedDocItem {
  title: string;
  url: string;
  section?: string | null;
  excerpt: string;
  score: number;
}

export interface DiagnosticCommand {
  label: string;
  command: string;
  language: string;
  description?: string | null;
}

export interface DiagnosticRunbook {
  title: string;
  summary?: string | null;
  steps: string[];
  commands: DiagnosticCommand[];
  read_only_verified: boolean;
}

export interface IssueNote {
  id: string;
  gitlab_note_id: number;
  author_username: string;
  author_name?: string | null;
  author_avatar_url?: string | null;
  body: string;
  is_internal: boolean;
  is_bot: boolean;
  created_at: string;
}

export interface ProposedAction {
  id: string;
  action_type: ProposedActionType;
  payload: Record<string, unknown>;
  is_destructive: boolean;
  status: ProposedActionStatus;
  approved_by?: string | null;
  approved_at?: string | null;
  retry_count: number;
  execution_result?: Record<string, unknown> | null;
  execution_error?: string | null;
  executed_at?: string | null;
  created_at: string;
}

export interface DuplicateItem {
  id: string;
  candidate_issue_id: string;
  candidate_iid: number;
  candidate_title: string;
  candidate_web_url: string;
  similarity_score: number;
  comparison_notes?: string | null;
}

export interface TriageAssessmentDetail {
  id: string;
  category: IssueCategory;
  priority: PriorityLevel;
  component: string;
  confidence: number;
  rag_max_score?: number | null;
  abstained: boolean;
  redaction_applied: boolean;
  summary: string;
  root_cause_analysis?: string | null;
  draft_reply_markdown: string;
  suggested_labels: string[];
  cited_docs: CitedDocItem[];
  diagnostic_runbook?: DiagnosticRunbook | null;
  latency_ms?: number | null;
  requires_human_approval: boolean;
  approval_status: ApprovalStatus;
  approved_by?: string | null;
  approved_at?: string | null;
  rejection_reason?: string | null;
  created_at: string;
  proposed_actions: ProposedAction[];
}

export interface IssueListItem {
  id: string;
  project_id: number;
  iid: number;
  title: string;
  state: string;
  author_username: string;
  labels: string[];
  web_url: string;
  status: IssueStatus;
  category?: IssueCategory | null;
  priority?: PriorityLevel | null;
  component?: string | null;
  confidence?: number | null;
  abstained: boolean;
  requires_approval: boolean;
  sla?: SLACountdown | null;
  created_at: string;
}

export interface IssueDetail {
  id: string;
  gitlab_id: number;
  project_id: number;
  iid: number;
  title: string;
  description?: string | null;
  redaction_applied: boolean;
  state: string;
  author_username: string;
  author_name?: string | null;
  author_avatar_url?: string | null;
  labels: string[];
  web_url: string;
  status: IssueStatus;
  created_at: string;
  updated_at: string;
  triaged_at?: string | null;
  sla?: SLACountdown | null;
  triage?: TriageAssessmentDetail | null;
  proposed_actions: ProposedAction[];
  notes: IssueNote[];
  duplicates: DuplicateItem[];
}

export interface ApproveActionRequest {
  action_ids?: string[] | null;
  edited_reply?: string | null;
  custom_labels?: string[] | null;
  override_category?: IssueCategory | null;
  override_priority?: PriorityLevel | null;
}

export interface ActionExecutionResultItem {
  action_id: string;
  action_type: ProposedActionType;
  status: ProposedActionStatus;
  execution_result?: Record<string, unknown> | null;
  error?: string | null;
}

export interface ApproveActionsResponse {
  status: string;
  executed_actions: ActionExecutionResultItem[];
  golden_example_created: boolean;
}

export interface ActionExecutionResponse {
  status: string;
  action: ProposedAction;
}

export interface RejectTriageRequest {
  reason?: string | null;
}

export interface RejectTriageResponse {
  status: string;
  message: string;
  issue_id: string;
}

export interface CloneIssueRequest {
  target_project_id: number;
  new_title?: string | null;
  additional_context?: string | null;
  inherit_labels?: boolean;
  cross_link?: boolean;
  execute_immediately?: boolean;
  source_issue_id?: string | null;
}

export interface ClonedTargetIssue {
  id: number;
  iid: number;
  project_id: number;
  title: string;
  web_url: string;
}

export interface CloneIssueResponse {
  status: string;
  target?: ClonedTargetIssue | null;
  proposed_action?: ProposedAction | null;
}

export interface ReTriageResponse {
  status: string;
  triage_id: string;
  confidence: number;
}

export interface RecentActivityItem {
  id: string;
  actor: string;
  event: string;
  entity_type: string;
  details: Record<string, unknown>;
  timestamp: string;
}

export interface DashboardStats {
  total_issues_ingested: number;
  auto_triaged_count: number;
  pending_approvals_count: number;
  auto_pilot_percentage: number;
  avg_triage_latency_seconds: number;
  sla_at_risk_count: number;
  sla_breached_count: number;
  docs_drift_clusters_count: number;
  at_risk_issues: IssueListItem[];
  category_distribution: Record<string, number>;
  priority_distribution: Record<string, number>;
  recent_activity: RecentActivityItem[];
}

export interface SSEPipelineEvent {
  id: string;
  event: string;
  actor: string;
  entity_type: string;
  entity_id: string;
  details: Record<string, unknown>;
  timestamp: string;
}

export interface DocChunkItem {
  id: string;
  source_type: string;
  title: string;
  source_url: string;
  section_header?: string | null;
  content_preview: string;
  created_at: string;
}

export interface CrawlRequest {
  source_type: CrawlerSourceType;
  url?: string | null;
}

export interface CrawlTriggerResponse {
  status: string;
  message: string;
  sync_run_id?: string | null;
}

export interface CrawlerSyncRun {
  id: string;
  source: string;
  base_url: string;
  pages_crawled: number;
  chunks_indexed: number;
  status: 'running' | 'completed' | 'failed';
  error_message?: string | null;
  triggered_by?: string | null;
  started_at: string;
  finished_at?: string | null;
}

export interface RAGPlaygroundRequest {
  query: string;
  top_k?: number;
  source_type?: string | null;
}

export interface RAGQueryResultItem {
  title: string;
  source_url: string;
  section_header?: string | null;
  content: string;
  similarity_score: number;
  source_type: string;
}

export interface RAGPlaygroundResponse {
  results: RAGQueryResultItem[];
  max_score: number;
  abstained: boolean;
}

export interface DocsDriftCluster {
  id: string;
  cluster_label: string;
  topic_summary: string;
  issue_count: number;
  avg_confidence: number;
  sample_issue_ids: string[];
  status: 'open' | 'draft_generated' | 'resolved' | 'dismissed';
  generated_doc_title?: string | null;
  generated_doc_draft?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocDraftResponse {
  cluster_id: string;
  title: string;
  markdown_draft: string;
  status: string;
}

export interface SLAPolicy {
  id?: string | null;
  priority: PriorityLevel;
  target_response_minutes: number;
  target_resolution_minutes: number;
  warning_threshold_pct: number;
  notify_slack: boolean;
  notify_gitlab_mention: boolean;
  escalation_mentions: string[];
  updated_at?: string | null;
}

export interface RoutingRule {
  id?: string | null;
  name: string;
  category?: IssueCategory | null;
  component?: string | null;
  priority?: PriorityLevel | null;
  target_project_id: number;
  target_project_name?: string | null;
  auto_labels: string[];
  is_active: boolean;
  priority_order: number;
}

export interface PlatformRulesConfig {
  auto_pilot_confidence_threshold: number;
  duplicate_similarity_threshold: number;
  rag_min_confidence: number;
  enable_auto_execution: boolean;
  sla_policies: SLAPolicy[];
  routing_rules: RoutingRule[];
}

export interface GoldenExample {
  id: string;
  issue_id?: string | null;
  triage_id?: string | null;
  issue_title: string;
  sanitized_issue_excerpt: string;
  original_category?: string | null;
  final_category: string;
  original_priority?: string | null;
  final_priority: string;
  original_labels: string[];
  final_labels: string[];
  original_reply?: string | null;
  edited_reply: string;
  diff_summary?: string | null;
  created_by: string;
  created_at: string;
}

export interface AuditLogEntry {
  id: string;
  entity_type: string;
  entity_id: string;
  actor: string;
  event: string;
  details: Record<string, unknown>;
  ip_address?: string | null;
  created_at: string;
}
