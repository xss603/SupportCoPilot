import React, { useEffect, useState } from 'react';
import {
  Inbox,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Flame,
  Layers,
  ArrowUpRight,
  TrendingUp,
} from 'lucide-react';
import { DashboardStats } from '../types';

interface CommandCenterProps {
  stats?: DashboardStats;
  onNavigateToQueue: () => void;
}

export const CommandCenter: React.FC<CommandCenterProps> = ({
  stats,
  onNavigateToQueue,
}) => {
  const [liveEvents, setLiveEvents] = useState<Array<any>>([]);

  // Subscribe to real-time Server-Sent Events (SSE)
  useEffect(() => {
    const sse = new EventSource('/api/v1/stats/events');
    sse.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLiveEvents((prev) => [data, ...prev].slice(0, 8));
      } catch (e) {
        console.error('SSE JSON error', e);
      }
    };
    return () => {
      sse.close();
    };
  }, []);

  const total = stats?.total_issues_ingested || 0;
  const autoTriaged = stats?.auto_triaged_count || 0;
  const pendingApprovals = stats?.pending_approvals_count || 0;
  const autoPilotPct = stats?.auto_pilot_percentage || 0;

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-[calc(100vh-3.5rem)]">
      {/* Overview Title */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">
            Platform Support Operations Cockpit
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time GitLab webhook telemetry, automated RAG diagnosis, and co-pilot execution queue.
          </p>
        </div>
        <button
          onClick={onNavigateToQueue}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium shadow-sm transition-all"
        >
          <span>Open Triage Queue</span>
          <ArrowUpRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-4 gap-4">
        {/* Card 1: Ingested Issues */}
        <div className="p-4 rounded-xl bg-white border border-border shadow-card hover:shadow-pop hover:-translate-y-0.5 transition-all duration-200">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Total Issues Monitored</span>
            <Inbox className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-slate-900">{total}</span>
            <span className="text-[11px] text-emerald-600 flex items-center font-medium">
              <TrendingUp className="w-3 h-3 mr-0.5" /> Live Ingest
            </span>
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Across connected GitLab projects</div>
        </div>

        {/* Card 2: Auto-Triaged % */}
        <div className="p-4 rounded-xl bg-white border border-border shadow-card hover:shadow-pop hover:-translate-y-0.5 transition-all duration-200">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Auto-Pilot Rate</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-emerald-600">{autoPilotPct}%</span>
            <span className="text-[11px] text-slate-500 font-mono">({autoTriaged} resolved)</span>
          </div>
          <div className="text-[10px] text-slate-500 mt-1">High-confidence grounded answers</div>
        </div>

        {/* Card 3: Pending Human Approval */}
        <div className="p-4 rounded-xl bg-white border border-border shadow-card hover:shadow-pop hover:-translate-y-0.5 transition-all duration-200">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Pending Co-Pilot Review</span>
            <AlertTriangle className="w-4 h-4 text-amber-600" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-amber-600">{pendingApprovals}</span>
            <span className="text-[11px] text-amber-600/80 font-medium">Drafts Ready</span>
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Gated by human-in-the-loop safety</div>
        </div>

        {/* Card 4: Avg Diagnosis Latency */}
        <div className="p-4 rounded-xl bg-white border border-border shadow-card hover:shadow-pop hover:-translate-y-0.5 transition-all duration-200">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Avg Pipeline Latency</span>
            <Clock className="w-4 h-4 text-cyan-600" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-cyan-600">
              {stats?.avg_triage_latency_seconds || 1.4}s
            </span>
            <span className="text-[11px] text-slate-500 font-mono">p95</span>
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Embedding + Hybrid RAG + LLM</div>
        </div>
      </div>

      {/* Two-Column Middle Section: Real-Time Stream & Distribution Breakdown */}
      <div className="grid grid-cols-3 gap-6">
        {/* Left 2 Cols: Live Pipeline Activity Feed */}
        <div className="col-span-2 p-5 rounded-xl bg-surface-100 border border-border/80 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                Live Event Pipeline Activity (SSE)
              </h2>
            </div>
            <span className="text-[10px] text-slate-500 font-mono">Stream: active</span>
          </div>

          <div className="space-y-2">
            {(liveEvents.length > 0 ? liveEvents : (stats?.recent_activity || [])).map(
              (event: any, i: number) => {
                return (
                  <div
                    key={event.id || i}
                    className="p-2.5 rounded-lg bg-surface-200/70 border border-border/60 flex items-center justify-between text-xs transition-all hover:border-slate-300"
                  >
                    <div className="flex items-center gap-3">
                      <div className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-indigo-500/10 text-indigo-600 border border-indigo-500/20">
                        {event.event || 'Triage Event'}
                      </div>
                      <span className="text-slate-800 font-medium">
                        {event.details?.title || `Entity ${event.entity_id || event.entity_type}`}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-slate-500 text-[11px] font-mono">
                      <span>{event.actor || 'ai:gemini'}</span>
                      <span>
                        {event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : 'now'}
                      </span>
                    </div>
                  </div>
                );
              }
            )}

            {liveEvents.length === 0 && (!stats?.recent_activity || stats.recent_activity.length === 0) && (
              <div className="py-8 text-center text-slate-500 text-xs">
                No recent events recorded. Webhook listener ready on <code className="text-indigo-600">/api/v1/webhooks/gitlab</code>.
              </div>
            )}
          </div>
        </div>

        {/* Right 1 Col: Category & Priority Distribution */}
        <div className="p-5 rounded-xl bg-surface-100 border border-border/80 space-y-5">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2 mb-3">
              <Layers className="w-3.5 h-3.5 text-indigo-600" />
              Category Breakdown
            </h2>
            <div className="space-y-2">
              {Object.entries(stats?.category_distribution || { bug: 4, configuration: 2, access_iam: 1 }).map(
                ([cat, count]) => (
                  <div key={cat} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-700 capitalize">{cat.replace('_', ' ')}</span>
                      <span className="font-mono text-slate-500 text-[11px]">{count}</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-indigo-500 rounded-full"
                        style={{ width: `${Math.min(100, (count / (total || 1)) * 100)}%` }}
                      ></div>
                    </div>
                  </div>
                )
              )}
            </div>
          </div>

          <div className="pt-3 border-t border-border">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2 mb-3">
              <Flame className="w-3.5 h-3.5 text-amber-600" />
              Severity Levels
            </h2>
            <div className="grid grid-cols-4 gap-2 text-center">
              {['P1', 'P2', 'P3', 'P4'].map((prio) => {
                const count = (stats?.priority_distribution || {})[prio] || 0;
                return (
                  <div key={prio} className="p-2 rounded-lg bg-surface-200 border border-border">
                    <div className="text-[10px] font-bold text-slate-500">{prio}</div>
                    <div className="text-sm font-bold font-mono text-slate-900 mt-0.5">{count}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
