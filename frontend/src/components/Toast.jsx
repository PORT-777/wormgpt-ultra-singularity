// @ts-nocheck
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import Icon from "./Icon.jsx";

const ToastCtx = createContext(null);

export function ToastProvider({ children }) {
  const [items, setItems] = useState([]);
  const timers = useRef(new Map());

  const remove = useCallback((id) => {
    const t = timers.current.get(id);
    if (t) clearTimeout(t);
    timers.current.delete(id);
    setItems((prev) => prev.filter((x) => x.id !== id));
  }, []);

  const push = useCallback((type, message, opts = {}) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const duration = opts.duration ?? 4000;
    setItems((prev) => [...prev.slice(-4), { id, type, message: String(message || ""), action: opts.action || null }]);
    if (duration > 0) {
      const t = setTimeout(() => remove(id), duration);
      timers.current.set(id, t);
    }
    return id;
  }, [remove]);

  const api = useMemo(() => ({
    success: (m, o) => push("success", m, o),
    error: (m, o) => push("error", m, o),
    info: (m, o) => push("info", m, o),
    remove,
  }), [push, remove]);

  useEffect(() => () => { timers.current.forEach((t) => clearTimeout(t)); }, []);

  return (
    <ToastCtx.Provider value={api}>
      {children}
      <div className="toast-host" aria-live="polite" aria-atomic="false">
        {items.map((t) => (
          <div key={t.id} className={`toast toast-${t.type}`} role={t.type === "error" ? "alert" : "status"}>
            <span className="toast-dot" />
            <span className="toast-msg">{t.message}</span>
            {t.action?.label && <button type="button" className="toast-action" onClick={() => { try { t.action.onClick?.(); } finally { remove(t.id); } }}>{t.action.label}</button>}
            <button type="button" className="toast-close" onClick={() => remove(t.id)} aria-label="إغلاق">
              <Icon name="close" size={13} />
            </button>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastCtx);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
