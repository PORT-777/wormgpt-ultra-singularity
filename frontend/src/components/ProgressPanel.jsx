// @ts-nocheck
import React, { useCallback, useEffect, useMemo, useState } from "react";
import Icon from "./Icon.jsx";
import { emitXp, getCatalog, getState, resetState } from "../gamification.js";

const METRIC_LABELS = {
  analyses: "Analyses",
  iocs: "IOCs extracted",
  yara: "YARA rules",
  sigma: "Sigma rules",
  hunts: "Threat hunts",
  reports: "Reports",
  attributions: "Attributions",
  sandbox_runs: "Sandbox runs",
  intel_lookups: "Intel lookups",
  re_sessions: "RE sessions",
  detections: "Detections deployed",
  packed_samples: "Packed samples",
  messages: "Messages",
  streak: "Day streak",
  challenges: "Challenges",
};

const panel = { border: "1px solid rgba(204,0,0,.25)", background: "rgba(10,0,0,.35)", borderRadius: 10, padding: 12 };
const muted = { fontSize: 11, color: "var(--text-2)" };

function Bar({ value, max, height = 8 }) {
  const pct = Math.max(0, Math.min(100, max > 0 ? (value / max) * 100 : 0));
  return (
    <div style={{ height, borderRadius: 999, background: "rgba(255,255,255,.06)", overflow: "hidden" }}>
      <div style={{ width: `${pct}%`, height: "100%", background: "linear-gradient(90deg,var(--accent),#ff6b6b)", boxShadow: "0 0 10px rgba(204,0,0,.45)" }} />
    </div>
  );
}

export default function ProgressPanel({ notify, onClose }) {
  const [state, setState] = useState(null);
  const [catalog, setCatalog] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [s, c] = await Promise.all([getState(), getCatalog()]);
    setState(s); setCatalog(c);
  }, []);

  useEffect(() => { load(); }, [load]);

  const levels = catalog?.levels || [];
  const achievements = catalog?.achievements || [];
  const counters = state?.counters || {};
  const unlocked = state?.achievements || {};
  const nextLevel = useMemo(() => levels.find((l) => l.level === (state?.level || 1) + 1) || null, [levels, state]);

  const doReset = async () => {
    if (!window.confirm("Reset all XP, achievements and streaks?")) return;
    setBusy(true);
    try { setState(await resetState()); notify?.("Progress reset.", "ok"); }
    catch (e) { notify?.(e.message || String(e), "error"); }
    finally { setBusy(false); }
  };

  if (!state) return <div className="panel-state" style={{ margin: "18px auto" }}><span className="spinner" /> Loading progress…</div>;

  return <div style={{ display: "grid", gap: 12 }}>
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
      <div className="side-title" style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 6 }}>
        <Icon name="trophy" size={14} /> Analyst Progress
        {state.source === "local" && <span className="pill" title="Backend unreachable — progress cached locally">offline cache</span>}
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button className="btn sm ghost" onClick={load} disabled={busy}><Icon name="refresh" size={13} /> Refresh</button>
        <button className="btn sm danger" onClick={doReset} disabled={busy}>Reset</button>
        {onClose && <button className="btn sm ghost" onClick={onClose}><Icon name="close" size={13} /></button>}
      </div>
    </div>

    <div style={{ ...panel, display: "grid", gap: 10 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <div style={{ width: 54, height: 54, borderRadius: 12, display: "grid", placeItems: "center", border: "1px solid rgba(204,0,0,.5)", background: "radial-gradient(circle at 30% 20%, rgba(204,0,0,.35), rgba(10,0,0,.6))", boxShadow: "0 0 18px rgba(204,0,0,.25)" }}>
          <div style={{ textAlign: "center", lineHeight: 1.05 }}>
            <div style={{ fontSize: 9, color: "var(--text-2)" }}>LVL</div>
            <div style={{ fontSize: 20, fontWeight: 800 }}>{state.level}</div>
          </div>
        </div>
        <div style={{ flex: 1, minWidth: 200 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8 }}>
            <b style={{ fontSize: 15 }}>{state.level_name}</b>
            <span style={muted}>{state.xp} XP{nextLevel ? ` · ${state.xp_to_next} to ${nextLevel.name}` : " · max level"}</span>
          </div>
          <div style={{ marginTop: 6 }}><Bar value={state.progress} max={100} height={10} /></div>
          <div style={{ ...muted, marginTop: 6, display: "flex", gap: 12, flexWrap: "wrap" }}>
            <span>🔥 streak: <b style={{ color: "var(--text)" }}>{state.streak}d</b></span>
            <span>🏆 achievements: <b style={{ color: "var(--text)" }}>{state.achievements_unlocked}/{state.achievements_total}</b></span>
            <span>last active: {state.last_active || "—"}</span>
          </div>
        </div>
      </div>
    </div>

    <div className="grid2" style={{ gap: 12 }}>
      <div style={panel}>
        <div className="side-title" style={{ fontSize: 11, marginBottom: 8 }}>Levels</div>
        <div style={{ display: "grid", gap: 6 }}>
          {levels.map((l) => {
            const active = l.level === state.level;
            const done = state.xp >= l.xp_required;
            return <div key={l.level} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, opacity: done ? 1 : .65 }}>
              <span className="pill" style={{ minWidth: 46, justifyContent: "center", borderColor: active ? "var(--accent)" : undefined, color: active ? "#fff" : undefined }}>{l.level}</span>
              <span style={{ flex: 1 }}>{l.name}</span>
              <span style={muted}>{l.xp_required} XP</span>
              {active && <Icon name="check" size={13} className="ok" />}
            </div>;
          })}
        </div>
      </div>

      <div style={panel}>
        <div className="side-title" style={{ fontSize: 11, marginBottom: 8 }}>Counters</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, fontSize: 12 }}>
          {Object.keys(METRIC_LABELS).filter((k) => counters[k] || ["analyses", "iocs", "yara", "sigma"].includes(k)).map((k) => (
            <div key={k} style={{ display: "flex", justifyContent: "space-between", gap: 6, padding: "3px 0", borderBottom: "1px solid rgba(255,255,255,.05)" }}>
              <span style={muted}>{METRIC_LABELS[k]}</span>
              <b>{counters[k] || 0}</b>
            </div>
          ))}
        </div>
      </div>
    </div>

    <div style={panel}>
      <div className="side-title" style={{ fontSize: 11, marginBottom: 8 }}>Achievements ({state.achievements_unlocked}/{state.achievements_total})</div>
      {achievements.length === 0 && <div style={muted}>Achievement catalog unavailable (backend offline).</div>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))", gap: 8 }}>
        {achievements.map((a) => {
          const isUnlocked = !!unlocked[a.id];
          const cur = counters[a.metric] || 0;
          return <div key={a.id} title={a.description} style={{ border: `1px solid ${isUnlocked ? "rgba(255,0,0,.55)" : "rgba(255,255,255,.08)"}`, borderRadius: 9, padding: 9, background: isUnlocked ? "rgba(204,0,0,.14)" : "rgba(255,255,255,.02)", boxShadow: isUnlocked ? "0 0 14px rgba(204,0,0,.18)" : "none" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 6 }}>
              <b style={{ fontSize: 12 }}>{isUnlocked ? "🏆 " : "🔒 "}{a.name}</b>
              <span style={{ ...muted, color: isUnlocked ? "#ffb4b4" : undefined }}>+{a.xp} XP</span>
            </div>
            <div style={{ ...muted, margin: "4px 0 6px", minHeight: 26 }}>{a.description}</div>
            <Bar value={Math.min(cur, a.threshold)} max={a.threshold} height={5} />
            <div style={{ ...muted, marginTop: 4 }}>{Math.min(cur, a.threshold)} / {a.threshold}</div>
          </div>;
        })}
      </div>
    </div>

    <div style={panel}>
      <div className="side-title" style={{ fontSize: 11, marginBottom: 8 }}>Recent XP</div>
      {(state.recent || []).length === 0 && <div style={muted}>No XP events yet. Run an analysis or extract IOCs to start earning.</div>}
      <div style={{ display: "grid", gap: 4, maxHeight: 200, overflow: "auto" }}>
        {[...(state.recent || [])].reverse().map((r, i) => (
          <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: 11, gap: 8, padding: "3px 0", borderBottom: "1px solid rgba(255,255,255,.04)" }}>
            <span>{r.event}</span>
            <span style={{ color: "#ff9a9a" }}>+{r.xp} XP</span>
          </div>
        ))}
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
        <button className="btn sm ghost" onClick={() => emitXp("message_sent")}>Test: +2 XP</button>
        <button className="btn sm ghost" onClick={() => emitXp("ioc_extracted")}>Test: IOC +5 XP</button>
      </div>
    </div>
  </div>;
}
