import React, { useState } from 'react';
import {
  BookOpen,
  Search,
  RefreshCw,
  ExternalLink,
  Sparkles,
  Database,
  Terminal,
  Layers,
} from 'lucide-react';
import { RAGQueryResultItem } from '../types';
import { queryRAGPlayground, triggerCrawl } from '../api';

export const KnowledgeExplorer: React.FC = () => {
  const [query, setQuery] = useState('502 bad gateway istio mtls ingress');
  const [results, setResults] = useState<RAGQueryResultItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isCrawling, setIsCrawling] = useState(false);
  const [crawlStatus, setCrawlStatus] = useState<string | null>(null);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    try {
      const data = await queryRAGPlayground(query);
      setResults(data.results);
    } catch (err: any) {
      console.error('RAG query failed', err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleCrawl = async (source: 'runbooks' | 'documentation' | 'academy') => {
    setIsCrawling(true);
    setCrawlStatus(`Initiated crawl for ${source}...`);
    try {
      await triggerCrawl(source);
      setCrawlStatus(`Sync job queued for ${source}!`);
    } catch (err: any) {
      setCrawlStatus(`Crawl error: ${err.message}`);
    } finally {
      setIsCrawling(false);
    }
  };

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-[calc(100vh-3.5rem)]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-indigo-600" />
            Documentation & Academy Knowledge Explorer
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Hybrid vector & full-text search index powering Gemini grounding. Test queries and inspect indexed chunks.
          </p>
        </div>

        {/* Sync Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleCrawl('runbooks')}
            disabled={isCrawling}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-medium transition-colors border border-border"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isCrawling ? 'animate-spin text-indigo-600' : ''}`} />
            <span>Re-Index Runbooks</span>
          </button>

          <button
            onClick={() => handleCrawl('documentation')}
            disabled={isCrawling}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-700 text-xs font-medium transition-colors border border-indigo-500/30"
          >
            <Database className="w-3.5 h-3.5" />
            <span>Sync Docs & Academy</span>
          </button>
        </div>
      </div>

      {crawlStatus && (
        <div className="p-3 rounded-lg bg-indigo-50/30 border border-indigo-500/30 text-indigo-700 text-xs font-mono">
          ℹ️ {crawlStatus}
        </div>
      )}

      {/* Live RAG Playground Card */}
      <div className="p-5 rounded-xl bg-surface-100 border border-border space-y-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-600" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">
              Live RAG Retrieval Playground
            </h2>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">
            Hybrid pgvector + Keyword (RRF)
          </span>
        </div>

        {/* Search Input Bar */}
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter search phrase or issue problem statement to inspect RAG ranking..."
              className="w-full pl-9 pr-4 py-2 bg-surface-200 border border-border rounded-lg text-xs text-slate-900 font-mono focus:outline-none focus:border-indigo-500"
            />
          </div>
          <button
            type="submit"
            disabled={isSearching}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition-all shadow-sm flex items-center gap-1.5"
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>{isSearching ? 'Retrieving...' : 'Run Query'}</span>
          </button>
        </form>

        {/* Results Stream */}
        <div className="space-y-3 pt-2">
          {results.length > 0 ? (
            results.map((res, idx) => (
              <div
                key={idx}
                className="p-4 rounded-lg bg-surface-200/70 border border-border/80 space-y-2 hover:border-slate-300 transition-all text-xs"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-slate-100 text-slate-700 font-mono text-[10px] flex items-center justify-center font-bold">
                      {idx + 1}
                    </span>
                    <a
                      href={res.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
                    >
                      <span>{res.title}</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                    {res.section_header && (
                      <span className="text-slate-500 text-[11px]">
                        › {res.section_header}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 font-mono text-[10px]">
                    <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 uppercase">
                      {res.source_type}
                    </span>
                    <span className="px-2 py-0.5 rounded font-bold bg-emerald-500/20 text-emerald-700 border border-emerald-500/30">
                      Score: {Math.round(res.similarity_score * 100)}%
                    </span>
                  </div>
                </div>

                <div className="p-3 rounded bg-surface-300/80 border border-border/60 text-slate-700 font-mono text-[11px] whitespace-pre-wrap leading-relaxed">
                  {res.content}
                </div>
              </div>
            ))
          ) : (
            <div className="py-8 text-center text-xs text-slate-500">
              Submit a query above to see ranked context chunks retrieved from PostgreSQL / pgvector.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
