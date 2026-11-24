import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Radar, Sparkles, Copy, FileWarning } from 'lucide-react';
import { fetchDocsDriftClusters, generateDocDraft } from '../api';
import { DocsDriftCluster } from '../types';
import { useToast } from './Toaster';

const statusStyle: Record<string, string> = {
  open: 'bg-amber-50 text-amber-700 border-amber-200',
  draft_generated: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  resolved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  dismissed: 'bg-slate-100 text-slate-500 border-slate-200',
};

export const DocsDriftRadar: React.FC = () => {
  const qc = useQueryClient();
  const toast = useToast();
  const [filter, setFilter] = useState('');
  const [selected, setSelected] = useState<DocsDriftCluster | undefined>();
  const { data = [], isLoading } = useQuery({ queryKey: ['drift', filter], queryFn: () => fetchDocsDriftClusters(filter || undefined) });
  const gen = useMutation({
    mutationFn: generateDocDraft,
    onSuccess: (r) => { toast('success', 'Doc draft generated'); qc.invalidateQueries({ queryKey: ['drift'] }); setSelected((s) => s && { ...s, generated_doc_title: r.title, generated_doc_draft: r.markdown_draft, status: 'draft_generated' }); },
    onError: () => toast('error', 'Draft generation failed'),
  });
  const draft = selected?.generated_doc_draft;

  return (
    <div className="h-full flex animate-in">
      <div className="w-[420px] border-r border-border bg-white/60 flex flex-col">
        <div className="p-4 border-b border-border">
          <div className="flex items-center gap-2 mb-3"><Radar className="w-4 h-4 text-indigo-600" /><h2 className="text-sm font-semibold">Docs Drift Radar</h2></div>
          <p className="text-[11px] text-slate-500 mb-3">Issues the knowledge base couldn't answer confidently (&lt; 0.65), grouped by topic.</p>
          <div className="flex gap-1.5">
            {['', 'open', 'draft_generated', 'resolved'].map((f) => (
              <button key={f} onClick={() => setFilter(f)} className={`px-2.5 py-1 rounded-full text-[11px] border ${filter === f ? 'bg-indigo-50 text-indigo-700 border-indigo-200' : 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50'}`}>{f ? f.replace('_', ' ') : 'all'}</button>
            ))}
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {isLoading && [0, 1, 2].map((i) => <div key={i} className="h-20 rounded-xl bg-slate-100 animate-pulse" />)}
          {!isLoading && data.length === 0 && (
            <div className="text-center py-16 text-slate-500 text-xs"><FileWarning className="w-8 h-8 mx-auto mb-2 text-slate-300" />No documentation gaps detected 🎉</div>
          )}
          {data.map((c) => (
            <button key={c.id} onClick={() => setSelected(c)} className={`w-full text-left p-3 rounded-xl border bg-white shadow-card hover:shadow-pop transition-all ${selected?.id === c.id ? 'border-indigo-300 ring-1 ring-indigo-200' : 'border-border'}`}>
              <div className="flex items-start justify-between gap-2">
                <span className="text-xs font-semibold text-slate-900">{c.cluster_label}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${statusStyle[c.status]}`}>{c.status.replace('_', ' ')}</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1 line-clamp-2">{c.topic_summary}</p>
              <div className="mt-2 flex items-center gap-3 text-[10px] text-slate-500">
                <span>{c.issue_count} issues</span>
                <div className="flex-1 h-1.5 rounded-full bg-slate-100 overflow-hidden"><div className="h-full bg-amber-400" style={{ width: `${Math.round(c.avg_confidence * 100)}%` }} /></div>
                <span className="font-mono">{Math.round(c.avg_confidence * 100)}% conf</span>
              </div>
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 p-6 overflow-y-auto">
        {!selected ? (
          <div className="h-full flex items-center justify-center text-xs text-slate-500">Select a cluster to review and draft documentation.</div>
        ) : (
          <div className="max-w-3xl space-y-4">
            <div className="flex items-start justify-between">
              <div><h3 className="text-base font-semibold">{selected.cluster_label}</h3><p className="text-xs text-slate-500 mt-1">{selected.topic_summary}</p></div>
              <button disabled={gen.isPending} onClick={() => gen.mutate(selected.id)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-sm disabled:opacity-60">
                <Sparkles className={`w-3.5 h-3.5 ${gen.isPending ? 'animate-pulse' : ''}`} />{gen.isPending ? 'Generating…' : draft ? 'Regenerate Draft' : 'Generate Doc Draft'}
              </button>
            </div>
            {draft ? (
              <div className="rounded-xl border border-border bg-white shadow-card">
                <div className="flex items-center justify-between px-4 py-2 border-b border-border">
                  <span className="text-xs font-medium">{selected.generated_doc_title}</span>
                  <button onClick={() => { navigator.clipboard.writeText(draft); toast('info', 'Draft copied'); }} className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-900"><Copy className="w-3 h-3" />Copy</button>
                </div>
                <pre className="p-4 text-xs text-slate-700 whitespace-pre-wrap font-mono leading-relaxed">{draft}</pre>
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-slate-300 p-10 text-center text-xs text-slate-500">No draft yet — generate one from the resolved ticket threads.</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
