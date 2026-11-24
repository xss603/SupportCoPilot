import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ScrollText, ChevronRight } from 'lucide-react';
import { fetchAuditLogs } from '../api';

export const AuditLogView: React.FC = () => {
  const [actor, setActor] = useState('');
  const [entity, setEntity] = useState('');
  const [open, setOpen] = useState<string | undefined>();
  const { data = [], isLoading } = useQuery({
    queryKey: ['audit', actor, entity],
    queryFn: () => fetchAuditLogs({ actor: actor || undefined, entity_type: entity || undefined, limit: 100 }),
    refetchInterval: 15000,
  });
  const input = 'px-3 py-1.5 bg-white border border-slate-200 rounded-md text-xs focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-200';
  return (
    <div className="h-full overflow-y-auto p-6 animate-in">
      <div className="max-w-5xl mx-auto space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2"><ScrollText className="w-4 h-4 text-indigo-600" /><h2 className="text-sm font-semibold">Audit Log</h2><span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">immutable</span></div>
          <div className="flex gap-2">
            <input className={input} placeholder="Filter actor…" value={actor} onChange={(e) => setActor(e.target.value)} />
            <input className={input} placeholder="Filter entity type…" value={entity} onChange={(e) => setEntity(e.target.value)} />
          </div>
        </div>
        <div className="rounded-xl border border-border bg-white shadow-card divide-y divide-border">
          {isLoading && [0, 1, 2, 3].map((i) => <div key={i} className="h-12 animate-pulse bg-slate-50" />)}
          {!isLoading && data.length === 0 && <div className="p-10 text-center text-xs text-slate-500">No audit events match your filters.</div>}
          {data.map((e) => (
            <div key={e.id}>
              <button onClick={() => setOpen(open === e.id ? undefined : e.id)} className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-slate-50 text-xs">
                <ChevronRight className={`w-3.5 h-3.5 text-slate-400 transition-transform ${open === e.id ? 'rotate-90' : ''}`} />
                <span className="font-mono text-[10px] text-slate-400 w-36">{new Date(e.created_at).toLocaleString()}</span>
                <span className="font-medium text-slate-800 w-44 truncate">{e.event}</span>
                <span className="px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 text-[10px]">{e.entity_type}</span>
                <span className="text-slate-500 ml-auto">{e.actor}</span>
              </button>
              {open === e.id && <pre className="px-12 pb-3 text-[11px] font-mono text-slate-600 whitespace-pre-wrap">{JSON.stringify(e.details, null, 2)}</pre>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
