import React from 'react';
import { Search, Command, RefreshCw, Radio, ExternalLink, DownloadCloud } from 'lucide-react';

interface HeaderProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onRefresh: () => void;
  onPull?: () => void;
  isPulling?: boolean;
  isFetching?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  searchQuery,
  onSearchChange,
  onRefresh,
  onPull,
  isPulling,
  isFetching,
}) => {
  return (
    <header className="h-14 px-6 bg-surface-200 border-b border-border flex items-center justify-between select-none">
      {/* Global Search Bar */}
      <div className="flex items-center gap-3 w-96">
        <div className="relative w-full">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            id="global-search"
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search issues, labels, runbooks, authors... (Press '/' to focus)"
            className="w-full pl-9 pr-12 py-1.5 bg-slate-50/90 border border-slate-200 rounded-md text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-indigo-500/80 focus:ring-1 focus:ring-indigo-500/50 transition-all"
          />
          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-slate-100 text-[10px] text-slate-500 font-mono border border-slate-200">
            <Command className="w-2.5 h-2.5" />
            <span>K</span>
          </div>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Live SSE Ingestion Badge */}
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-slate-50/60 border border-slate-200 text-[11px] text-slate-700">
          <Radio className="w-3 h-3 text-emerald-600 animate-pulse" />
          <span className="font-mono text-slate-500 text-[10px]">SSE Stream:</span>
          <span className="text-emerald-600 font-medium">Connected</span>
        </div>

        {/* Manual Pull from GitLab */}
        <button
          onClick={onPull}
          disabled={isPulling}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium shadow-sm disabled:opacity-60"
          title="Pull new issues from GitLab now"
        >
          <DownloadCloud className={`w-3.5 h-3.5 ${isPulling ? 'animate-bounce' : ''}`} />
          <span>{isPulling ? 'Pulling…' : 'Pull from GitLab'}</span>
        </button>

        {/* Manual Refresh Button */}
        <button
          onClick={onRefresh}
          disabled={isFetching}
          className="p-1.5 rounded-md hover:bg-slate-100 text-slate-500 hover:text-slate-900 transition-colors"
          title="Refresh Data"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin text-indigo-600' : ''}`} />
        </button>

        {/* GitLab Portal Link */}
        <a
          href="https://gitlab.com"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-700 border border-indigo-500/30 text-xs font-medium transition-all"
        >
          <span>Open GitLab</span>
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </header>
  );
};
