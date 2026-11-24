import React, { useEffect } from 'react';
import {
  Inbox,
  AlertCircle,
  CheckCircle,
  Clock,
  Sparkles,
  ExternalLink,
  ChevronRight,
} from 'lucide-react';
import { IssueListItem } from '../types';

interface TriageQueueProps {
  issues: IssueListItem[];
  selectedIssueId?: string;
  onSelectIssue: (issue: IssueListItem) => void;
  statusFilter: string;
  onStatusFilterChange: (s: string) => void;
  isLoading: boolean;
}

export const TriageQueue: React.FC<TriageQueueProps> = ({
  issues,
  selectedIssueId,
  onSelectIssue,
  statusFilter,
  onStatusFilterChange,
  isLoading,
}) => {
  // Keyboard Navigation: J / K shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't intercept if typing in an input/textarea
      if (['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName)) return;

      if (e.key === 'j' || e.key === 'ArrowDown') {
        e.preventDefault();
        const currentIndex = issues.findIndex((i) => i.id === selectedIssueId);
        if (currentIndex < issues.length - 1) {
          onSelectIssue(issues[currentIndex + 1]);
        }
      } else if (e.key === 'k' || e.key === 'ArrowUp') {
        e.preventDefault();
        const currentIndex = issues.findIndex((i) => i.id === selectedIssueId);
        if (currentIndex > 0) {
          onSelectIssue(issues[currentIndex - 1]);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [issues, selectedIssueId, onSelectIssue]);

  const filterTabs = [
    { id: '', label: 'All Issues' },
    { id: 'pending_approval', label: 'Pending Approval' },
    { id: 'auto_resolved', label: 'Auto-Resolved' },
    { id: 'human_review', label: 'Human Review' },
  ];

  return (
    <div className="flex flex-col h-full bg-surface-200 border-r border-border select-none">
      {/* Top Filter Bar */}
      <div className="p-3 border-b border-border bg-surface-300 flex items-center justify-between">
        <div className="flex items-center gap-1 overflow-x-auto">
          {filterTabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onStatusFilterChange(tab.id)}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
                statusFilter === tab.id
                  ? 'bg-indigo-50 text-indigo-700 shadow-sm border border-indigo-200'
                  : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="text-[10px] text-slate-500 font-mono hidden sm:flex items-center gap-1.5">
          <span>Shortcuts:</span>
          <kbd className="px-1 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-700">J</kbd>
          <kbd className="px-1 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-700">K</kbd>
        </div>
      </div>

      {/* Issues Master List */}
      <div className="flex-1 overflow-y-auto divide-y divide-border/60">
        {isLoading ? (
          <div className="p-8 text-center text-xs text-slate-500">Loading issues...</div>
        ) : issues.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500 space-y-2">
            <Inbox className="w-6 h-6 mx-auto text-slate-500" />
            <p>No issues found matching the active filter.</p>
          </div>
        ) : (
          issues.map((issue) => {
            const isSelected = issue.id === selectedIssueId;
            const confidence = issue.confidence ? Math.round(issue.confidence * 100) : null;

            return (
              <div
                key={issue.id}
                onClick={() => onSelectIssue(issue)}
                className={`p-3.5 cursor-pointer transition-all border-l-2 ${
                  isSelected
                    ? 'bg-indigo-50/70 border-l-indigo-500 shadow-sm'
                    : 'hover:bg-surface-100 border-l-transparent'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1 min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-mono text-slate-500 font-semibold">
                        #{issue.iid}
                      </span>
                      {issue.priority && (
                        <span
                          className={`text-[9px] font-bold px-1.5 py-0.2 rounded font-mono ${
                            issue.priority === 'P1'
                              ? 'bg-rose-500/20 text-rose-600 border border-rose-500/30'
                              : issue.priority === 'P2'
                              ? 'bg-amber-500/20 text-amber-700 border border-amber-500/30'
                              : 'bg-slate-100 text-slate-500'
                          }`}
                        >
                          {issue.priority}
                        </span>
                      )}
                      <span className="text-xs font-medium text-slate-800 truncate">
                        {issue.title}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-[11px] text-slate-500">
                      <span>@{issue.author_username}</span>
                      <span>•</span>
                      <span>{new Date(issue.created_at).toLocaleDateString()}</span>
                      {confidence !== null && (
                        <>
                          <span>•</span>
                          <span
                            className={`flex items-center gap-0.5 font-mono text-[10px] ${
                              confidence >= 85 ? 'text-emerald-600' : 'text-amber-600'
                            }`}
                          >
                            <Sparkles className="w-2.5 h-2.5" />
                            {confidence}%
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-1.5">
                    {issue.status === 'auto_resolved' && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-600 border border-emerald-500/20 flex items-center gap-1">
                        <CheckCircle className="w-2.5 h-2.5" /> Resolved
                      </span>
                    )}
                    {issue.status === 'pending_approval' && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-500/10 text-amber-700 border border-amber-500/20 flex items-center gap-1">
                        <Clock className="w-2.5 h-2.5" /> Co-Pilot
                      </span>
                    )}
                    {issue.status === 'human_review' && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-rose-500/10 text-rose-600 border border-rose-500/20 flex items-center gap-1">
                        <AlertCircle className="w-2.5 h-2.5" /> Manual
                      </span>
                    )}
                    <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
