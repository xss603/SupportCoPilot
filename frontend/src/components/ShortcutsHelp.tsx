import React from 'react';
import { X } from 'lucide-react';

const rows: [string, string][] = [
  ['⌘/Ctrl K', 'Open command palette'], ['/', 'Focus search'], ['1 – 6', 'Switch view'],
  ['J / K', 'Next / previous issue'], ['A', 'Approve actions'], ['C', 'Clone ticket'], ['E', 'Edit draft'], ['?', 'Show this help'], ['Esc', 'Close dialogs'],
];

export const ShortcutsHelp: React.FC<{ open: boolean; onClose: () => void }> = ({ open, onClose }) => {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[90] bg-slate-900/30 backdrop-blur-sm flex items-center justify-center" onClick={onClose}>
      <div className="animate-in w-full max-w-sm bg-white rounded-xl border border-border shadow-pop" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <h3 className="text-sm font-semibold">Keyboard shortcuts</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-slate-100 text-slate-500"><X className="w-4 h-4" /></button>
        </div>
        <ul className="p-3 space-y-1">
          {rows.map(([k, d]) => (
            <li key={k} className="flex items-center justify-between px-2 py-1.5 text-xs">
              <span className="text-slate-600">{d}</span>
              <kbd className="px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-700 font-mono text-[10px]">{k}</kbd>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};
