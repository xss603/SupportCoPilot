import React from 'react';
import {
  LayoutDashboard,
  Inbox,
  BookOpen,
  Settings,
  GitBranch,
  ShieldCheck,
  Zap,
  Radar,
  ScrollText,
} from 'lucide-react';

export type NavTab = 'command_center' | 'triage_queue' | 'knowledge' | 'drift' | 'audit' | 'settings';

interface SidebarProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  pendingCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  pendingCount = 0,
}) => {
  const navItems = [
    {
      id: 'command_center' as NavTab,
      label: 'Command Center',
      icon: LayoutDashboard,
      badge: null,
    },
    {
      id: 'triage_queue' as NavTab,
      label: 'Triage Queue',
      icon: Inbox,
      badge: pendingCount > 0 ? pendingCount : null,
    },
    {
      id: 'knowledge' as NavTab,
      label: 'Docs & Academy',
      icon: BookOpen,
      badge: null,
    },
    {
      id: 'drift' as NavTab,
      label: 'Docs Drift Radar',
      icon: Radar,
      badge: null,
    },
    {
      id: 'audit' as NavTab,
      label: 'Audit Log',
      icon: ScrollText,
      badge: null,
    },
    {
      id: 'settings' as NavTab,
      label: 'Guardrails & Rules',
      icon: Settings,
      badge: null,
    },
  ];

  return (
    <aside className="w-64 bg-surface-300 border-r border-border flex flex-col justify-between select-none">
      <div>
        {/* Brand Header */}
        <div className="h-14 px-4 flex items-center gap-3 border-b border-border">
          <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-600 font-bold">
            <Zap className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-semibold tracking-wider text-slate-900 uppercase">
              GitLab Triage
            </div>
            <div className="text-[10px] text-slate-500 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              Platform Co-Pilot
            </div>
          </div>
        </div>

        {/* Navigation List */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-700 shadow-sm border border-indigo-200'
                    : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-600' : 'text-slate-500'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge !== null && (
                  <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded-full bg-amber-500/20 text-amber-700 border border-amber-500/30">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Operational Mode Badge */}
      <div className="p-3 border-t border-border bg-surface-200/50">
        <div className="rounded-lg p-2.5 bg-slate-50/60 border border-slate-200 text-[11px] space-y-1.5">
          <div className="flex items-center justify-between text-slate-700">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              Guardrails
            </span>
            <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-600 font-mono">
              Active
            </span>
          </div>
          <div className="text-[10px] text-slate-500">
            Human approval required for public comments & ticket cloning.
          </div>
        </div>
      </div>
    </aside>
  );
};
