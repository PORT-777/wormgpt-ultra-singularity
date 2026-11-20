// @ts-nocheck
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Icon from "./Icon.jsx";

const K = {
  run_start: { i: "spark", l: "Run", c: "var(--accent)" },
  plan: { i: "activity", l: "Plan", c: "#60a5fa" },
  plan_step: { i: "activity", l: "Step", c: "#60a5fa" },
  thought: { i: "spark", l: "Thought", c: "#a78bfa" },
  action: { i: "terminal", l: "Action", c: "#f59e0b" },
  observation: { i: "check", l: "Observation", c: "#34d399" },
  reflection: { i: "history", l: "Reflection", c: "#22d3ee" },
  memory: { i: "folder", l: "Memory", c: "#94a3b8" },
  crew: { i: "shield", l: "Crew", c: "#f472b6" },
  review: { i: "check", l: "Review", c: "#34d399" },
  status: { i: "activity", l: "Status", c: "#60a5fa" },
  stream: { i: "spark", l: "Stream", c: "#a78bfa" },
  final: { i: "check", l: "Final", c: "#22c55e" },
  error: { i: "close", l: "Error", c: "#f87171" },
  done: { i: "check", l: "Done", c: "#22c55e" },
};

function toText(v) {
  if (v == null) return "";
  if (typeof v === "string") return v;
  try { return JSON.stringify(v, null, 2); } catch { return String(v); }
}

function fmtTs(ts) {
  if (!ts) return "";
  try {
    const n = Number(ts);
    const d = new Date(n > 1e12 ? n : n * 1000);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch { return ""; }
}

function shortRun(id) {
  const s = String(id || "");
  return s ? s.slice(0, 8) : "—";
}

export default function TracePanel({ trace = [], status = {}, planSteps = [], endRef, sessionId = null, authToken = "", onLoadTimeline = null }) {
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [replay, setReplay] = useState(false);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [runs, setRuns] = useState([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const [selectedRun, setSelectedRun] = useState("");
  const [source, setSource] = useState("live"); // live | persisted
  const playRef = useRef(null);

  const fetchRuns = useCallback(async (sid = sessionId) => {
    if (!sid) { setRuns([]); return []; }
    setRunsLoading(true);
    try {
      const r = await fetch(`/api/history/${encodeURIComponent(sid)}/runs?limit=2000`, {
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
        cache: "no-store",
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(j?.detail || j?.error || `HTTP ${r.status}`);
      const list = Array.isArray(j?.runs) ? j.runs : [];
      setRuns(list);
      return list;
    } catch {
      setRuns([]);
      return [];
    } finally {
      setRunsLoading(false);
    }
  }, [sessionId, authToken]);

  useEffect(() => { if (sessionId) fetchRuns(sessionId); else { setRuns([]); setSelectedRun(""); setSource("live"); } }, [sessionId, fetchRuns]);

  const normalized = useMemo(() => {
    return (Array.isArray(trace) ? trace : []).map((step, i) => {
      const kind = step?.kind || step?.type || "thought";
      const body = step?.text ?? step?.data ?? step?.args ?? step?.output ?? "";
      const tool = step?.tool || (step?.data && step.data.tool) || "";
      const ts = step?.ts || step?.time || step?.timestamp || null;
      const runId = step?.run_id || step?.runId || "";
      const seq = step?.seq ?? (i + 1);
      const text = toText(body);
      const m = K[kind] || K.thought;
      return { ...step, _i: i, kind, text, tool, ts, runId, seq, _label: m.l, _icon: m.i, _color: m.c };
    });
  }, [trace]);

  const runOptions = useMemo(() => {
    const fromTrace = Array.from(new Set(normalized.map(x => x.runId).filter(Boolean)));
    const fromRuns = runs.map(r => r.run_id).filter(Boolean);
    const all = Array.from(new Set([...fromRuns, ...fromTrace]));
    // preserve runs order when available
    const ordered = runs.map(r => r.run_id).filter(id => all.includes(id));
    for (const id of all) if (!ordered.includes(id)) ordered.unshift(id);
    return ordered;
  }, [normalized, runs]);

  const kinds = useMemo(() => {
    const s = new Set(normalized.map(x => x.kind));
    return ["all", ...Array.from(s)];
  }, [normalized]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return normalized.filter(x => {
      if (selectedRun && String(x.runId || "") !== String(selectedRun)) return false;
      if (filter !== "all" && x.kind !== filter) return false;
      if (!q) return true;
      return (x.text || "").toLowerCase().includes(q) || (x.tool || "").toLowerCase().includes(q) || (x.kind || "").toLowerCase().includes(q) || String(x.runId || "").toLowerCase().includes(q);
    });
  }, [normalized, filter, query, selectedRun]);

  const visible = replay ? filtered.slice(0, Math.max(0, Math.min(cursor, filtered.length))) : filtered;

  useEffect(() => {
    if (!replay) setCursor(filtered.length);
    else setCursor(c => Math.min(c || 0, filtered.length));
  }, [filtered.length, replay]);

  useEffect(() => {
    if (!playing || !replay) return;
    if (cursor >= filtered.length) { setPlaying(false); return; }
    playRef.current = setTimeout(() => setCursor(c => Math.min(filtered.length, c + 1)), 450);
    return () => clearTimeout(playRef.current);
  }, [playing, replay, cursor, filtered.length]);

  useEffect(() => () => clearTimeout(playRef.current), []);

  const copy = async (t) => { try { await navigator.clipboard.writeText(t || ""); } catch {} };

  const exportJson = () => {
    try {
      const payload = { session_id: sessionId, selected_run: selectedRun || null, source, exported_at: new Date().toISOString(), events: visible, total_in_view: filtered.length };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `timeline-${sessionId || "session"}${selectedRun ? `-${selectedRun.slice(0,8)}` : ""}.json`; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {}
  };

  const loadTimeline = async (runId = selectedRun) => {
    if (!sessionId) return;
    if (onLoadTimeline) {
      setLoading(true);
      try {
        await onLoadTimeline(runId || "");
        setSource("persisted");
        setSelectedRun(runId || "");
        await fetchRuns(sessionId);
        setReplay(false); setPlaying(false);
      } finally { setLoading(false); }
      return;
    }
    // fallback: no handler
  };

  const selectRun = async (runId) => {
    setSelectedRun(runId);
    setReplay(false); setPlaying(false);
    // if persisted source or explicit run load desired, reload from backend for that run
    if (sessionId && runId) {
      await loadTimeline(runId);
    } else if (sessionId && !runId && source === "persisted") {
      await loadTimeline("");
    }
  };

  const stats = useMemo(() => {
    const by = {};
    for (const x of filtered) by[x.kind] = (by[x.kind] || 0) + 1;
    return by;
  }, [filtered]);

  const activeRunMeta = useMemo(() => runs.find(r => r.run_id === selectedRun) || null, [runs, selectedRun]);

  return (
    <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "8px 12px", borderBottom: "1px solid var(--border, #2a2a2a)", display: "grid", gap: 8 }}>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
          <button type="button" className="btn sm ghost" onClick={() => loadTimeline(selectedRun || "")} disabled={!sessionId || loading} title="Load persisted timeline for session/run">
            <Icon name="history" size={12} /> {loading ? "Loading…" : "Timeline"}
          </button>
          <button type="button" className="btn sm ghost" onClick={() => fetchRuns()} disabled={!sessionId || runsLoading} title="Refresh runs list"><Icon name="refresh" size={12} /> {runsLoading ? "…" : "Runs"}</button>
          <button type="button" className={`btn sm ${replay ? "" : "ghost"}`} onClick={() => { setReplay(r => !r); setPlaying(false); }} title="Step replay mode"><Icon name="activity" size={12} /> Replay</button>
          {replay && <>
            <button type="button" className="btn sm ghost" onClick={() => setPlaying(p => !p)}>{playing ? "Pause" : "Play"}</button>
            <button type="button" className="btn sm ghost" onClick={() => setCursor(c => Math.max(0, c - 1))}>-1</button>
            <button type="button" className="btn sm ghost" onClick={() => setCursor(c => Math.min(filtered.length, c + 1))}>+1</button>
          </>}
          <button type="button" className="btn sm ghost" onClick={exportJson} title="Export visible timeline JSON"><Icon name="copy" size={12} /> Export</button>
          <span className="pill" title="Visible / filtered / total">{visible.length}/{filtered.length}/{normalized.length}</span>
          <span className="pill" title="Trace source">{source}</span>
        </div>

        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
          <select value={selectedRun} onChange={e => selectRun(e.target.value)} className="inp" style={{ minHeight: 28, fontSize: 12, flex: 1, minWidth: 160 }} title="Select run (persisted replay-by-run)">
            <option value="">All runs / live</option>
            {runOptions.map((rid) => {
              const meta = runs.find(r => r.run_id === rid);
              const label = meta ? `${shortRun(rid)} · ${meta.count} ev · ${meta.has_error ? "err" : (meta.has_final ? "ok" : "…")}` : shortRun(rid);
              return <option key={rid} value={rid}>{label}</option>;
            })}
          </select>
          {activeRunMeta ? <span className="pill" title="Selected run stats">{activeRunMeta.count} events{activeRunMeta.has_error ? " · error" : ""}{activeRunMeta.has_final ? " · final" : ""}</span> : null}
        </div>

        {replay && (
          <input type="range" min={0} max={filtered.length} value={Math.min(cursor, filtered.length)} onChange={e => { setCursor(Number(e.target.value)); setPlaying(false); }} style={{ width: "100%" }} />
        )}
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Filter trace text/tool/run…" className="inp" style={{ flex: 1, minWidth: 120, minHeight: 28, padding: "4px 8px", fontSize: 12 }} />
          <select value={filter} onChange={e => setFilter(e.target.value)} className="inp" style={{ minHeight: 28, fontSize: 12, maxWidth: 160 }}>
            {kinds.map(k => <option key={k} value={k}>{k === "all" ? `All (${filtered.length})` : `${k} (${stats[k] || 0})`}</option>)}
          </select>
        </div>
      </div>

      <div style={{ flex: 1, minHeight: 0, overflow: "auto", padding: 12, display: "grid", gap: 8, alignContent: "start" }}>
        {planSteps.length > 0 && (
          <div className="card">
            <div className="side-title" style={{ fontSize: 12, marginBottom: 8 }}>Execution plan</div>
            <div style={{ display: "grid", gap: 4 }}>
              {planSteps.map(s => (
                <div key={s.id} style={{ display: "flex", gap: 8, fontSize: 12, color: s.state === "done" ? "var(--text)" : s.state === "failed" ? "#fca5a5" : "var(--text-2)" }}>
                  <span style={{ width: 14 }}>{s.state === "done" ? "✓" : s.state === "running" ? "•" : s.state === "failed" ? "×" : "○"}</span>
                  <span>{s.title || s.id}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {!visible.length && <div className="muted" style={{ fontSize: 12 }}>No trace events {normalized.length ? "for current run/filter/replay position" : "yet"}. Run a task or load persisted timeline/runs.</div>}

        {visible.map((step, i) => {
          const text = step.text || "";
          const short = text.length > 220 ? text.slice(0, 220) + "…" : text;
          return (
            <div key={step.id || `${step.runId || "r"}-${step.seq || i}-${i}`} className="tool-card" style={{ borderLeft: `3px solid ${step._color || "var(--border)"}` }}>
              <div className="tool-head" style={{ gap: 6, flexWrap: "wrap" }}>
                <Icon name={step._icon} size={13} />
                <span style={{ textTransform: "uppercase", letterSpacing: ".05em", fontSize: 10, color: step._color }}>{step._label}</span>
                {step.tool ? <span className="kbd">{step.tool}</span> : null}
                {step.runId ? <span className="kbd" title="run id">run:{shortRun(step.runId)}</span> : null}
                {step.seq != null ? <span className="muted" style={{ fontSize: 10 }}>#{step.seq}</span> : null}
                {step.ts ? <span className="muted" style={{ fontSize: 10, marginLeft: "auto" }}>{fmtTs(step.ts)}</span> : null}
                {text ? <button className="btn sm ghost" style={{ minHeight: 20, padding: "0 6px", marginLeft: step.ts ? 0 : "auto" }} onClick={() => copy(text)} title="Copy"><Icon name="copy" size={12} /></button> : null}
              </div>
              {text ? (
                <details open={text.length <= 260 || step.kind === "error" || step.kind === "final" || step.kind === "run_start"}>
                  <summary style={{ cursor: "pointer", fontSize: 12, color: "var(--text-2)", padding: "4px 0", listStyle: "none" }}>{short.split("\n")[0] || "(details)"}</summary>
                  <pre className="tool-body" style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: 12 }}>{text}</pre>
                </details>
              ) : null}
            </div>
          );
        })}

        {(status.state === "thinking" || status.state === "executing_tool" || status.state === "planning" || status.state === "reflecting") && (
          <div style={{ color: "var(--accent)", fontSize: 12 }}>Working… {status.state}</div>
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}
