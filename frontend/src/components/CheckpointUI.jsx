// @ts-nocheck
import React, { useCallback, useEffect, useMemo, useState } from "react";

async function api(url, opts = {}) {
  const res = await fetch(url, opts);
  const ct = res.headers.get("content-type") || "";
  const data = ct.includes("application/json") ? await res.json().catch(() => ({})) : await res.text();
  if (!res.ok) throw new Error((data && (data.detail || data.error)) || `HTTP ${res.status}`);
  return data;
}

export function useCheckpoints(sessionId) {
  const [items, setItems] = useState([]);
  const load = useCallback(async () => {
    if (!sessionId) return setItems([]);
    try {
      const d = await api(`/api/checkpoints?session_id=${encodeURIComponent(sessionId)}`);
      setItems(Array.isArray(d?.checkpoints) ? d.checkpoints : []);
    } catch {
      setItems([]);
    }
  }, [sessionId]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const h = () => load();
    window.addEventListener("xxxgpt:checkpoints-refresh", h);
    return () => window.removeEventListener("xxxgpt:checkpoints-refresh", h);
  }, [load]);
  return { items, reload: load };
}

function fmtTime(ts) {
  try { return new Date((ts || 0) * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); }
  catch { return "—"; }
}

function DiffView({ diff }) {
  const lines = String(diff || "").split("\n");
  return (
    <pre className="ckpt-diff-pre" aria-label="Unified diff">
      {lines.map((line, i) => {
        let cls = "ckpt-diff-line";
        if (line.startsWith("+++ ") || line.startsWith("--- ")) cls += " head";
        else if (line.startsWith("@@")) cls += " hunk";
        else if (line.startsWith("+")) cls += " add";
        else if (line.startsWith("-")) cls += " del";
        return <div key={i} className={cls}>{line || " "}</div>;
      })}
    </pre>
  );
}

export function CheckpointDiffModal({ checkpoint, sessionId, onClose, onReverted, toast }) {
  const [diff, setDiff] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!checkpoint) return;
    let alive = true;
    setLoading(true); setError("");
    api(`/api/checkpoints/${encodeURIComponent(checkpoint.id)}/diff?session_id=${encodeURIComponent(sessionId || checkpoint.session_id || "")}`)
      .then((d) => alive && setDiff(d?.diff || ""))
      .catch((e) => alive && setError(e.message || "diff failed"))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [checkpoint, sessionId]);
  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  if (!checkpoint) return null;
  const files = checkpoint.files || [];
  return (
    <div className="overlay ckpt-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="ckpt-modal" role="dialog" aria-modal="true" aria-label="Checkpoint diff">
        <div className="ckpt-modal-head">
          <div style={{ minWidth: 0 }}>
            <div style={{ fontWeight: 700 }}>Diff · {checkpoint.id}</div>
            <div className="muted" style={{ fontSize: 12 }}>{fmtTime(checkpoint.ts)} · {files.length} files · {checkpoint.message_id || "—"}</div>
          </div>
          <div className="row">
            <button className="btn sm ghost" onClick={onClose}>Close (Esc)</button>
          </div>
        </div>
        <div className="ckpt-modal-body">
          {loading ? <div className="panel-state"><span className="spinner" /> Loading diff…</div>
            : error ? <div className="panel-state error">{error}</div>
            : <DiffView diff={diff} />}
        </div>
      </div>
    </div>
  );
}

export function CheckpointChips({ message, sessionId, toast, onAfterRevert }) {
  const cps = useMemo(() => Array.isArray(message?.checkpoints) ? message.checkpoints : (message?.checkpoint ? [message.checkpoint] : []), [message]);
  const [open, setOpen] = useState(null);
  const revert = async (cp) => {
    if (!window.confirm(`Revert to checkpoint ${cp.id}? Current files will be backed up first (pre-revert snapshot).`)) return;
    try {
      const r = await api(`/api/checkpoints/${encodeURIComponent(cp.id)}/revert?session_id=${encodeURIComponent(sessionId || cp.session_id || "")}`, { method: "POST" });
      const n = (r?.restored || []).length;
      toast?.success?.(`تم الاسترجاع ↩ ${n} ملفات`);
      window.dispatchEvent(new Event("xxxgpt:checkpoints-refresh"));
      window.dispatchEvent(new Event("files-changed"));
      window.dispatchEvent(new Event("xxxgpt:history-refresh"));
      onAfterRevert?.(r);
    } catch (e) {
      toast?.error?.(e.message || "Revert failed");
    }
  };
  if (!cps.length) return null;
  return (
    <>
      <div className="ckpt-row">
        {cps.map((cp) => (
          <div key={cp.id} className="ckpt-chip" title={cp.id}>
            <span className="ckpt-chip-meta">⏱ {fmtTime(cp.ts)} · {(cp.files || []).length} files</span>
            <button type="button" className="btn sm ghost ckpt-act" onClick={() => setOpen(cp)}>👁 Diff</button>
            <button type="button" className="btn sm ghost ckpt-act" onClick={() => revert(cp)}>↩ Revert</button>
          </div>
        ))}
      </div>
      {open && <CheckpointDiffModal checkpoint={open} sessionId={sessionId} onClose={() => setOpen(null)} toast={toast} />}
    </>
  );
}