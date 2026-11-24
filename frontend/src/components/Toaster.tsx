import React, { createContext, useCallback, useContext, useState } from 'react';
import { CheckCircle2, AlertTriangle, Info, X } from 'lucide-react';

type Kind = 'success' | 'error' | 'info';
interface Toast { id: number; kind: Kind; message: string }
const Ctx = createContext<(kind: Kind, message: string) => void>(() => {});
export const useToast = () => useContext(Ctx);

const styles: Record<Kind, string> = {
  success: 'border-emerald-200 text-emerald-800',
  error: 'border-rose-200 text-rose-800',
  info: 'border-indigo-200 text-indigo-800',
};
const icons = { success: CheckCircle2, error: AlertTriangle, info: Info };

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const dismiss = (id: number) => setToasts((t) => t.filter((x) => x.id !== id));
  const push = useCallback((kind: Kind, message: string) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, kind, message }]);
    setTimeout(() => dismiss(id), 4000);
  }, []);
  return (
    <Ctx.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2">
        {toasts.map((t) => {
          const Icon = icons[t.kind];
          return (
            <div key={t.id} className={`animate-in flex items-center gap-2 pl-3 pr-2 py-2 rounded-lg bg-white border shadow-pop text-xs font-medium ${styles[t.kind]}`}>
              <Icon className="w-4 h-4" />
              <span>{t.message}</span>
              <button onClick={() => dismiss(t.id)} className="p-1 rounded hover:bg-slate-100 text-slate-400"><X className="w-3 h-3" /></button>
            </div>
          );
        })}
      </div>
    </Ctx.Provider>
  );
};
