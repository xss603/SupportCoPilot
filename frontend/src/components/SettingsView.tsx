import React, { useState } from 'react';
import {
  Shield,
  Sliders,
  Key,
  GitFork,
  CheckCircle2,
  AlertTriangle,
  Save,
} from 'lucide-react';

export const SettingsView: React.FC = () => {
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.85);
  const [autoPilotEnabled, setAutoPilotEnabled] = useState(false);
  const [savedNotice, setSavedNotice] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 3000);
  };

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-[calc(100vh-3.5rem)] max-w-4xl">
      {/* Title */}
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
          <Shield className="w-5 h-5 text-indigo-600" />
          Automation Rules & Guardrails Settings
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Tune AI confidence thresholds, routing policies, and human-in-the-loop approval gates.
        </p>
      </div>

      {savedNotice && (
        <div className="p-3 rounded-lg bg-emerald-50/30 border border-emerald-500/30 text-emerald-700 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          Settings successfully persisted!
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Guardrail 1: Auto-Pilot Threshold */}
        <div className="p-5 rounded-xl bg-surface-100 border border-border space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-indigo-600" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                Confidence Threshold & Approval Gate
              </h2>
            </div>
            <span className="text-xs font-mono font-bold text-indigo-600">
              {Math.round(confidenceThreshold * 100)}%
            </span>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-xs text-slate-500">
              <span>Conservative (0.95)</span>
              <span>Balanced (0.85)</span>
              <span>Aggressive (0.70)</span>
            </div>
            <input
              type="range"
              min="0.5"
              max="1.0"
              step="0.05"
              value={confidenceThreshold}
              onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
              className="w-full accent-indigo-500 cursor-pointer"
            />
          </div>

          <div className="p-3 rounded-lg bg-surface-200 border border-border/80 text-[11px] text-slate-700 space-y-1">
            <div className="font-semibold text-slate-800">Threshold Policy:</div>
            <div>
              Issues diagnosed with confidence ≥ <span className="font-mono text-emerald-600">{Math.round(confidenceThreshold * 100)}%</span> will be eligible for automatic label application.
            </div>
            <div>
              Issues below this score are automatically routed to the <span className="font-mono text-amber-700">Co-Pilot Review Queue</span>.
            </div>
          </div>
        </div>

        {/* Guardrail 2: Operational Mode Toggle */}
        <div className="p-5 rounded-xl bg-surface-100 border border-border space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                Auto-Pilot Direct Execution
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Allow the platform to automatically post public GitLab comments without manual review when confidence is high.
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={autoPilotEnabled}
                onChange={(e) => setAutoPilotEnabled(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-slate-100 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
            </label>
          </div>

          {!autoPilotEnabled ? (
            <div className="p-3 rounded-lg bg-indigo-50/20 border border-indigo-500/20 text-indigo-700 text-[11px]">
              🔒 <strong>Co-Pilot Active:</strong> The AI drafts responses, cites documentation, and prepares labels, but a support engineer must click <em>"Approve & Execute"</em> before mutations reach GitLab.
            </div>
          ) : (
            <div className="p-3 rounded-lg bg-amber-50/30 border border-amber-500/30 text-amber-700 text-[11px] flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              <span>
                <strong>Warning:</strong> High-confidence responses will be published directly to GitLab without human intervention.
              </span>
            </div>
          )}
        </div>

        {/* Project Routing Mappings */}
        <div className="p-5 rounded-xl bg-surface-100 border border-border space-y-4">
          <div className="flex items-center gap-2">
            <GitFork className="w-4 h-4 text-indigo-600" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">
              Downstream Escalation Routing Rules
            </h2>
          </div>

          <div className="space-y-2 text-xs">
            <div className="grid grid-cols-2 gap-3 p-3 rounded-lg bg-surface-200 border border-border">
              <div>
                <span className="text-slate-500 text-[10px] uppercase font-bold">Category</span>
                <div className="font-medium text-slate-800 mt-0.5">Bug (Networking / Ingress)</div>
              </div>
              <div>
                <span className="text-slate-500 text-[10px] uppercase font-bold">Default Escalation Repo</span>
                <div className="font-mono text-indigo-600 mt-0.5">caris4ops/cicd-helm-deploy (79988314)</div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 p-3 rounded-lg bg-surface-200 border border-border">
              <div>
                <span className="text-slate-500 text-[10px] uppercase font-bold">Category</span>
                <div className="font-medium text-slate-800 mt-0.5">Access / IAM / Certificates</div>
              </div>
              <div>
                <span className="text-slate-500 text-[10px] uppercase font-bold">Default Escalation Repo</span>
                <div className="font-mono text-indigo-600 mt-0.5">caris4ops/vault-cert-automation (79988306)</div>
              </div>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            type="submit"
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-sm transition-all"
          >
            <Save className="w-3.5 h-3.5" />
            <span>Save Rules & Guardrails</span>
          </button>
        </div>
      </form>
    </div>
  );
};
