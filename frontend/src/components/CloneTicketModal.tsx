import React, { useState } from 'react';
import { X, Copy, ExternalLink, GitBranch, ArrowRight } from 'lucide-react';
import { IssueDetail } from '../types';

interface CloneTicketModalProps {
  issue?: IssueDetail;
  isOpen: boolean;
  onClose: () => void;
  onClone: (payload: {
    target_project_id: number;
    new_title?: string;
    additional_context?: string;
    inherit_labels?: boolean;
  }) => Promise<void>;
}

export const CloneTicketModal: React.FC<CloneTicketModalProps> = ({
  issue,
  isOpen,
  onClose,
  onClone,
}) => {
  if (!isOpen || !issue) return null;

  const [targetProjectId, setTargetProjectId] = useState<number>(issue.project_id);
  const [newTitle, setNewTitle] = useState(`[Escalated] ${issue.title}`);
  const [operatorNotes, setOperatorNotes] = useState('');
  const [inheritLabels, setInheritLabels] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onClone({
        target_project_id: Number(targetProjectId),
        new_title: newTitle,
        additional_context: operatorNotes,
        inherit_labels: inheritLabels,
      });
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-surface-100 border border-border rounded-xl w-full max-w-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="p-4 border-b border-border bg-surface-200/80 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Copy className="w-4 h-4 text-indigo-600" />
            <h3 className="text-sm font-semibold text-slate-900">
              Clone / Escalate Issue #{issue.iid}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs">
          {/* Source Info */}
          <div className="p-3 rounded-lg bg-surface-300 border border-border text-[11px] text-slate-700 flex items-center justify-between font-mono">
            <span>Source: #{issue.iid} ({issue.title.slice(0, 35)}...)</span>
            <span>Current Project: {issue.project_id}</span>
          </div>

          {/* Target Project ID */}
          <div className="space-y-1.5">
            <label className="font-medium text-slate-700">Target Project ID / Downstream Repo</label>
            <input
              type="number"
              required
              value={targetProjectId}
              onChange={(e) => setTargetProjectId(Number(e.target.value))}
              placeholder="e.g. 86868711"
              className="w-full p-2 bg-surface-200 border border-border rounded-md text-slate-900 font-mono focus:outline-none focus:border-indigo-500"
            />
          </div>

          {/* Title */}
          <div className="space-y-1.5">
            <label className="font-medium text-slate-700">Escalated Ticket Title</label>
            <input
              type="text"
              required
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="w-full p-2 bg-surface-200 border border-border rounded-md text-slate-900 font-mono focus:outline-none focus:border-indigo-500"
            />
          </div>

          {/* Additional Operator Notes */}
          <div className="space-y-1.5">
            <label className="font-medium text-slate-700">
              Additional Technical Details & Reproduction Steps
            </label>
            <textarea
              rows={4}
              value={operatorNotes}
              onChange={(e) => setOperatorNotes(e.target.value)}
              placeholder="Add any specific namespace, logs, or triage instructions for the downstream development team..."
              className="w-full p-2 bg-surface-200 border border-border rounded-md text-slate-900 font-mono focus:outline-none focus:border-indigo-500"
            />
          </div>

          {/* Checkboxes */}
          <div className="space-y-2 pt-1">
            <label className="flex items-center gap-2 cursor-pointer text-slate-700">
              <input
                type="checkbox"
                checked={inheritLabels}
                onChange={(e) => setInheritLabels(e.target.checked)}
                className="rounded border-slate-200 text-indigo-600 focus:ring-0"
              />
              <span>Inherit labels from parent support issue</span>
            </label>
            <div className="text-[10px] text-slate-500 pl-5">
              An automatic bidirectional link will be cross-posted on both GitLab tickets.
            </div>
          </div>

          {/* Footer Actions */}
          <div className="pt-4 border-t border-border flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-all shadow-sm"
            >
              <ArrowRight className="w-3.5 h-3.5" />
              <span>{isSubmitting ? 'Cloning...' : 'Create Escalated Issue'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
