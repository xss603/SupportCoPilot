import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Check,
  X,
  ExternalLink,
  BookOpen,
  GitPullRequest,
  Copy,
  AlertTriangle,
  RotateCw,
  Send,
  Tag,
  Shield,
  Layers,
} from 'lucide-react';
import { IssueDetail } from '../types';

interface SplitPaneWorkbenchProps {
  issue?: IssueDetail;
  isLoading: boolean;
  onApprove: (issueId: string, editedReply?: string, customLabels?: string[]) => Promise<void>;
  onReject: (issueId: string, reason?: string) => Promise<void>;
  onOpenCloneModal: (issue: IssueDetail) => void;
  onReTriage: (issueId: string) => Promise<void>;
}

export const SplitPaneWorkbench: React.FC<SplitPaneWorkbenchProps> = ({
  issue,
  isLoading,
  onApprove,
  onReject,
  onOpenCloneModal,
  onReTriage,
}) => {
  const [draftReply, setDraftReply] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState<'diagnosis' | 'citations' | 'actions'>('diagnosis');

  // Sync draft reply when selected issue changes
  useEffect(() => {
    if (issue?.triage?.draft_reply_markdown) {
      setDraftReply(issue.triage.draft_reply_markdown);
    } else {
      setDraftReply('');
    }
  }, [issue]);

  // Keyboard shortcut listener: 'A' to approve, 'C' to clone
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName)) return;

      if ((e.key === 'a' || e.key === 'A') && issue) {
        e.preventDefault();
        handleApproveClick();
      } else if ((e.key === 'c' || e.key === 'C') && issue) {
        e.preventDefault();
        onOpenCloneModal(issue);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [issue, draftReply]);

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center text-xs text-slate-500">
        Loading issue context and AI triage...
      </div>
    );
  }

  if (!issue) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-slate-500 text-xs space-y-2">
        <Sparkles className="w-8 h-8 text-slate-500" />
        <p className="font-medium text-slate-700">Select an issue from the Triage Queue</p>
        <p className="text-[11px] text-slate-500 max-w-sm">
          Navigate using keyboard shortcuts <kbd className="px-1 py-0.5 rounded bg-slate-100 text-slate-700">J</kbd> and{' '}
          <kbd className="px-1 py-0.5 rounded bg-slate-100 text-slate-700">K</kbd> to inspect AI resolutions.
        </p>
      </div>
    );
  }

  const triage = issue.triage;
  const confidence = triage ? Math.round(triage.confidence * 100) : 0;

  const handleApproveClick = async () => {
    if (!issue) return;
    setIsSubmitting(true);
    try {
      await onApprove(issue.id, draftReply);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRejectClick = async () => {
    if (!issue) return;
    setIsSubmitting(true);
    try {
      await onReject(issue.id, 'Rejected by operator');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-background">
      {/* Top Issue Header Bar */}
      <div className="h-14 px-6 border-b border-border bg-surface-200/90 flex items-center justify-between select-none">
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-xs font-mono font-bold text-slate-500 bg-slate-100/80 px-2 py-0.5 rounded border border-slate-200">
            #{issue.iid}
          </span>
          <h2 className="text-sm font-semibold text-slate-900 truncate">{issue.title}</h2>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onReTriage(issue.id)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs transition-colors"
            title="Re-run Gemini AI Triage"
          >
            <RotateCw className="w-3 h-3" />
            <span>Re-Triage</span>
          </button>

          <a
            href={issue.web_url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs transition-colors"
          >
            <span>View on GitLab</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>

      {/* Main Split-Pane Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* ================= LEFT PANE: ORIGINAL ISSUE & CONTEXT ================= */}
        <div className="w-1/2 p-6 border-r border-border overflow-y-auto space-y-5 bg-surface-300/30">
          {/* Duplicate / Clone Alert Box */}
          {issue.duplicates && issue.duplicates.length > 0 && (
            <div className="p-3.5 rounded-lg bg-amber-50/20 border border-amber-500/30 text-xs space-y-2">
              <div className="flex items-center justify-between text-amber-700 font-semibold">
                <span className="flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                  Potential Duplicate / Related Issues Detected
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-700">
                  {issue.duplicates.length} Match(es)
                </span>
              </div>
              <div className="space-y-1.5 pt-1">
                {issue.duplicates.map((dup) => (
                  <div
                    key={dup.id}
                    className="flex items-center justify-between p-2 rounded bg-slate-900/20 border border-amber-500/20 text-[11px]"
                  >
                    <div className="flex items-center gap-2 truncate">
                      <span className="font-mono text-amber-700">#{dup.candidate_iid}</span>
                      <span className="text-slate-800 truncate">{dup.candidate_title}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-[10px] font-mono text-amber-600 font-bold">
                        {Math.round(dup.similarity_score * 100)}% Match
                      </span>
                      <a
                        href={dup.candidate_web_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-slate-500 hover:text-slate-900"
                      >
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Author & Metadata Card */}
          <div className="p-3 rounded-lg bg-surface-100 border border-border text-xs flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-full bg-indigo-600/30 text-indigo-700 flex items-center justify-center font-bold text-xs uppercase">
                {issue.author_username.slice(0, 2)}
              </div>
              <div>
                <div className="text-slate-800 font-medium">{issue.author_name || issue.author_username}</div>
                <div className="text-[10px] text-slate-500">@{issue.author_username}</div>
              </div>
            </div>

            <div className="text-right text-[11px] text-slate-500 font-mono">
              <div>Created: {new Date(issue.created_at).toLocaleString()}</div>
              <div>Project ID: {issue.project_id}</div>
            </div>
          </div>

          {/* Existing Labels */}
          {issue.labels && issue.labels.length > 0 && (
            <div className="space-y-1.5">
              <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                Current Labels
              </div>
              <div className="flex flex-wrap gap-1.5">
                {issue.labels.map((lbl) => (
                  <span
                    key={lbl}
                    className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-slate-100 text-slate-700 border border-slate-200"
                  >
                    {lbl}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Original Markdown Description */}
          <div className="space-y-2">
            <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
              Issue Description
            </div>
            <div className="p-4 rounded-lg bg-surface-100 border border-border text-xs text-slate-800 leading-relaxed font-mono whitespace-pre-wrap">
              {issue.description || '(No description provided in GitLab issue)'}
            </div>
          </div>
        </div>

        {/* ================= RIGHT PANE: AI COPILOT WORKBENCH ================= */}
        <div className="w-1/2 p-6 flex flex-col justify-between overflow-y-auto space-y-5 bg-surface-200/40">
          <div className="space-y-5">
            {/* AI Diagnosis Header Card */}
            {triage ? (
              <div className="p-4 rounded-xl bg-surface-100 border border-border shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-indigo-600" />
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-900">
                      Gemini 2.5 Diagnostic Assessment
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                        confidence >= 85
                          ? 'bg-emerald-500/20 text-emerald-700 border border-emerald-500/30'
                          : 'bg-amber-500/20 text-amber-700 border border-amber-500/30'
                      }`}
                    >
                      {confidence}% Confidence
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 uppercase">
                      {triage.category}
                    </span>
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-rose-500/20 text-rose-600 border border-rose-500/30">
                      {triage.priority}
                    </span>
                  </div>
                </div>

                <div className="text-xs text-slate-700 font-medium">
                  {triage.summary}
                </div>

                {triage.root_cause_analysis && (
                  <div className="p-2.5 rounded bg-surface-300/80 border border-border/80 text-[11px] text-slate-700 font-mono">
                    <span className="text-indigo-600 font-bold">RCA: </span>
                    {triage.root_cause_analysis}
                  </div>
                )}
              </div>
            ) : (
              <div className="p-6 rounded-lg bg-surface-100 border border-border text-center text-xs text-slate-500">
                AI Triage pending or in progress...
              </div>
            )}

            {/* Cited Knowledge & Runbooks Section */}
            {triage && triage.cited_docs && triage.cited_docs.length > 0 && (
              <div className="space-y-2">
                <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5 text-indigo-600" />
                  Cited Documentation & Academy Sources ({triage.cited_docs.length})
                </div>
                <div className="space-y-2">
                  {triage.cited_docs.map((doc, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg bg-surface-100 border border-border/80 text-xs space-y-1 hover:border-slate-300 transition-all"
                    >
                      <div className="flex items-center justify-between">
                        <a
                          href={doc.url}
                          target="_blank"
                          rel="noreferrer"
                          className="font-medium text-indigo-600 hover:text-indigo-800 flex items-center gap-1 text-[11px]"
                        >
                          <span>{doc.title}</span>
                          <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                        <span className="text-[10px] font-mono text-slate-500">
                          Match: {Math.round(doc.score * 100)}%
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-700 line-clamp-2 font-mono">
                        {doc.excerpt || doc.section}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Editable Draft Response */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                <span>Proposed GitLab Comment (Editable)</span>
                <span className="text-[10px] text-slate-500 font-mono">Markdown supported</span>
              </div>
              <textarea
                value={draftReply}
                onChange={(e) => setDraftReply(e.target.value)}
                rows={8}
                placeholder="Draft AI resolution reply..."
                className="w-full p-3 bg-surface-100 border border-border rounded-lg text-xs text-slate-900 font-mono focus:outline-none focus:border-indigo-500/80 focus:ring-1 focus:ring-indigo-500/50 leading-relaxed"
              />
            </div>

            {/* Proposed Labels to Apply */}
            {triage?.suggested_labels && (
              <div className="space-y-1.5">
                <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wider flex items-center gap-1">
                  <Tag className="w-3 h-3 text-indigo-600" />
                  Proposed Labels to Apply
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {triage.suggested_labels.map((lbl) => (
                    <span
                      key={lbl}
                      className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-500/10 text-indigo-700 border border-indigo-500/20"
                    >
                      +{lbl}
                    </span>
                  ))}
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-700 border border-emerald-500/20">
                    +ai-triaged
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Bottom Execution Action Bar */}
          <div className="pt-4 border-t border-border flex items-center justify-between select-none">
            <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-mono">
              <span>Shortcuts:</span>
              <kbd className="px-1 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-700">A</kbd> Approve
              <kbd className="px-1 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-700 ml-1">C</kbd> Clone
            </div>

            <div className="flex items-center gap-2.5">
              <button
                onClick={handleRejectClick}
                disabled={isSubmitting}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-100 hover:bg-rose-50 text-slate-700 hover:text-rose-700 border border-slate-200 hover:border-rose-500/30 text-xs font-medium transition-all"
              >
                <X className="w-3.5 h-3.5" />
                <span>Reject</span>
              </button>

              <button
                onClick={() => onOpenCloneModal(issue)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-200 text-xs font-medium transition-all"
              >
                <Copy className="w-3.5 h-3.5 text-indigo-600" />
                <span>Clone / Escalate</span>
              </button>

              <button
                onClick={handleApproveClick}
                disabled={isSubmitting}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-sm transition-all"
              >
                <Check className="w-3.5 h-3.5" />
                <span>Approve & Execute</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
