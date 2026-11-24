import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Search, CornerDownLeft } from 'lucide-react';

export interface PaletteItem { id: string; label: string; hint?: string; group: string; run: () => void }

export const CommandPalette: React.FC<{ open: boolean; onClose: () => void; items: PaletteItem[] }> = ({ open, onClose, items }) => {
  const [q, setQ] = useState('');
  const [idx, setIdx] = useState(0);
  const ref = useRef<HTMLInputElement>(null);
  const filtered = useMemo(
    () => items.filter((i) => (i.label + ' ' + (i.hint ?? '') + ' ' + i.group).toLowerCase().includes(q.toLowerCase())),
    [items, q]
  );
  useEffect(() => { if (open) { setQ(''); setIdx(0); setTimeout(() => ref.current?.focus(), 0); } }, [open]);
  useEffect(() => setIdx(0), [q]);
  if (!open) return null;
  const exec = (i?: PaletteItem) => { if (i) { onClose(); i.run(); } };
  return (
    <div className="fixed inset-0 z-[90] bg-slate-900/30 backdrop-blur-sm flex items-start justify-center pt-[15vh]" onClick={onClose}>
      <div className="animate-in w-full max-w-lg bg-white rounded-xl border border-border shadow-pop overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2 px-3 border-b border-border">
          <Search className="w-4 h-4 text-slate-400" />
          <input
            ref={ref}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown') { e.preventDefault(); setIdx((i) => Math.min(i + 1, filtered.length - 1)); }
              if (e.key === 'ArrowUp') { e.preventDefault(); setIdx((i) => Math.max(i - 1, 0)); }
              if (e.key === 'Enter') exec(filtered[idx]);
              if (e.key === 'Escape') onClose();
            }}
            placeholder="Type a command or search…"
            className="flex-1 py-3 text-sm bg-transparent outline-none placeholder:text-slate-400"
          />
          <kbd className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-500">Esc</kbd>
        </div>
        <div className="max-h-80 overflow-y-auto p-1.5">
          {filtered.length === 0 && <div className="p-6 text-center text-xs text-slate-500">No matching commands</div>}
          {filtered.map((i, n) => (
            <button
              key={i.id}
              onMouseEnter={() => setIdx(n)}
              onClick={() => exec(i)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-xs text-left ${n === idx ? 'bg-indigo-50 text-indigo-700' : 'text-slate-700'}`}
            >
              <span className="flex items-center gap-2">
                <span className="text-[10px] uppercase tracking-wide text-slate-400 w-16">{i.group}</span>
                <span className="font-medium">{i.label}</span>
              </span>
              {n === idx ? <CornerDownLeft className="w-3 h-3" /> : i.hint && <kbd className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-500">{i.hint}</kbd>}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
