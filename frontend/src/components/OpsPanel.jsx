// @ts-nocheck
import React, { useCallback, useEffect, useMemo, useState } from "react";
import Icon from "./Icon.jsx";
import { emitXp } from "../gamification.js";

async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  const tok = localStorage.getItem("🔥😈 PORT 777 EVIL ☠️🔥👹_token");
  if (tok) headers.Authorization = `Bearer ${tok}`;
  const res = await fetch(path, { ...opts, headers });
  const ct = res.headers.get("content-type") || "";
  const data = ct.includes("application/json") ? await res.json().catch(() => null) : await res.text().catch(() => null);
  if (!res.ok) throw new Error((data && (data.detail || data.error)) || `HTTP ${res.status}`);
  return data;
}
const runSec = (action, params = {}) => api("/api/security/run", { method: "POST", body: JSON.stringify({ action, params }) });

const panel = { border: "1px solid rgba(204,0,0,.25)", background: "rgba(10,0,0,.35)", borderRadius: 10, padding: 12 };
const label = { fontSize: 11, color: "var(--text-2)", marginBottom: 4 };
const ta = { width: "100%", minHeight: 110, fontFamily: "var(--mono)", fontSize: 12 };
const pre = { margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: 11, maxHeight: 280, overflow: "auto", fontFamily: "var(--mono)" };

const TYPE_COLOR = {
  ips: "#ff3b3b", domains: "#ff7676", urls: "#ff9f43", hashes: "#ff4d6d",
  md5: "#ff4d6d", sha1: "#ff4d6d", sha256: "#ff4d6d", cves: "#ff8fa3",
  emails: "#ff7b7b", paths: "#ffb3b3", wallets: "#ff5c8a", registry: "#ff9999",
};

function copyText(t, notify) {
  navigator.clipboard?.writeText(String(t || ""))
    .then(() => notify?.("Copied", "ok"))
    .catch(() => notify?.("Copy failed", "error"));
}

function HashTool({ notify }) {
  const [raw, setRaw] = useState("");
  const [out, setOut] = useState(null);
  const [busy, setBusy] = useState(false);
  const run = async (kind) => {
    const text = raw.trim();
    if (!text) return notify?.("Paste a hash, hex blob or text first", "warn");
    setBusy(true);
    try {
      const r = kind === "id"
        ? await runSec("hash_id", { value: text.split(/\s+/)[0] })
        : await runSec("hashes", { text });
      setOut({ kind, ...r });
      emitXp("intel_lookup");
      notify?.(kind === "id" ? "Hash identified" : "Hashes computed", "ok");
    } catch (e) { notify?.(e.message || String(e), "error"); }
    finally { setBusy(false); }
  };
  return <div style={{ display: "grid", gap: 10 }}>
    <div style={panel}>
      <div style={label}>Hash / hex / text — identify a hash format or compute MD5/SHA1/SHA256/SHA512 (+ fuzzy hashes)</div>
      <textarea className="input" style={ta} value={raw} onChange={(e) => setRaw(e.target.value)} placeholder="d41d8cd98f00b204e9800998ecf8427e  —  or  4d5a9000…  —  or any text" />
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
        <button className="btn sm" onClick={() => run("id")} disabled={busy}>{busy ? "…" : "Identify hash"}</button>
        <button className="btn sm ghost" onClick={() => run("hash")} disabled={busy}>Compute hashes</button>
        <button className="btn sm ghost" onClick={() => copyText(JSON.stringify(out, null, 2), notify)} disabled={!out}>Copy result</button>
      </div>
    </div>
    <div style={panel}>
      <div className="side-title" style={{ fontSize: 11, marginBottom: 8 }}>Result</div>
      {!out && <div style={label}>No lookup yet.</div>}
      {out && <pre style={pre}>{JSON.stringify(out, null, 2)}</pre>}
    </div>
  </div>;
}

function GraphTool({ notify }) {
  const [text, setText] = useState("");
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState(null);

  const build = async () => {
    if (!text.trim()) return notify?.("Paste text/logs to extract indicators", "warn");
    setBusy(true);
    try {
      const r = await runSec("iocs", { text });
      const cats = r?.categories || {};
      const list = [];
      Object.entries(cats).forEach(([type, vals]) => {
        (Array.isArray(vals) ? vals : []).slice(0, 14).forEach((v) => {
          if (v != null && String(v) !== "") list.push({ type, value: String(v) });
        });
      });
      const uniq = [];
      const seen = new Set();
      list.forEach((n) => { const k = `${n.type}:${n.value}`; if (!seen.has(k)) { seen.add(k); uniq.push(n); } });
      const cap = uniq.slice(0, 42);
      const W = 760, H = 420, cx = W / 2, cy = H / 2;
      const placed = cap.map((n, i) => {
        const angle = (i / Math.max(1, cap.length)) * Math.PI * 2;
        const ring = 120 + (i % 3) * 55;
        return { ...n, x: cx + Math.cos(angle) * ring, y: cy + Math.sin(angle) * ring * .72, id: i };
      });
      const links = placed.map((n) => ({ a: -1, b: n.id }));
      // Mesh: connect indicators of the same family so clusters are visible.
      placed.forEach((a, i) => placed.forEach((b, j) => {
        if (j <= i) return;
        const sameType = a.type === b.type;
        const sameSubnet = /ip/i.test(a.type) && a.value.split(".").slice(0, 3).join(".") === b.value.split(".").slice(0, 3).join(".");
        const sameDomain = /domain/i.test(a.type) && a.value.split(".").slice(-2).join(".") === b.value.split(".").slice(-2).join(".");
        if (sameType && (sameSubnet || sameDomain || (!/ip|domain/i.test(a.type) && Math.abs(i - j) < 3))) {
          links.push({ a: i, b: j });
        }
      }));
      setNodes(placed); setEdges(links); setSelected(null);
      emitXp("ioc_extracted");
      notify?.(`Graph: ${placed.length} indicators, ${links.length} links`, "ok");
    } catch (e) { notify?.(e.message || String(e), "error"); }
    finally { setBusy(false); }
  };

  const download = () => {
    const blob = new Blob([JSON.stringify({ nodes, edges }, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = "ioc-graph.json";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 800);
  };

  return <div style={{ display: "grid", gap: 10 }}>
    <div style={panel}>
      <div style={label}>Paste text, logs or an alert — indicators are extracted and linked into a graph (IP subnets, shared domains, same type)</div>
      <textarea className="input" style={ta} value={text} onChange={(e) => setText(e.target.value)} placeholder="hxxp://evil[.]example/a  ·  185.220.101.7  ·  d41d8cd98f00b204e9800998ecf8427e …" />
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
        <button className="btn sm" onClick={build} disabled={busy}><Icon name="graph" size={13} /> {busy ? "Building…" : "Build graph"}</button>
        <button className="btn sm ghost" onClick={download} disabled={!nodes.length}>Export JSON</button>
        <span style={{ ...label, alignSelf: "center" }}>{nodes.length} nodes · {edges.length} edges</span>
      </div>
    </div>
    <div style={panel}>
      {!nodes.length && <div style={label}>No graph yet — extract IOCs to render the network.</div>}
      {!!nodes.length && <svg viewBox="0 0 760 420" width="100%" height="420" style={{ background: "radial-gradient(circle at 50% 45%, rgba(204,0,0,.08), transparent 60%)", borderRadius: 8 }}>
        <circle cx="380" cy="210" r="26" fill="rgba(204,0,0,.22)" stroke="#ff3b3b" strokeWidth="1.5" />
        <text x="380" y="214" textAnchor="middle" fontSize="10" fill="#ffd6d6">CASE</text>
        {edges.map((e, i) => {
          const a = e.a < 0 ? { x: 380, y: 210 } : nodes[e.a];
          const b = nodes[e.b];
          if (!a || !b) return null;
          return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="rgba(255,60,60,.22)" strokeWidth="1" />;
        })}
        {nodes.map((n) => (
          <g key={n.id} onClick={() => { setSelected(n); copyText(n.value, notify); }} style={{ cursor: "pointer" }}>
            <circle cx={n.x} cy={n.y} r={6} fill={TYPE_COLOR[n.type] || "#ff6b6b"} opacity=".9" />
            <text x={n.x + 9} y={n.y + 3} fontSize="8" fill={selected?.id === n.id ? "#fff" : "#c9c9c9"}>
              {n.value.length > 26 ? `${n.value.slice(0, 26)}…` : n.value}
            </text>
          </g>
        ))}
      </svg>}
      {selected && <div style={{ ...label, marginTop: 6 }}>
        selected: <b style={{ color: "#ffb4b4" }}>{selected.type}</b> = <code>{selected.value}</code> · click copies
      </div>}
    </div>
  </div>;
}

function TimelineTool({ notify, sessionId }) {
  const [items, setItems] = useState([]);
  const [raw, setRaw] = useState("");
  const [busy, setBusy] = useState(false);

  const fromSession = useCallback(async () => {
    if (!sessionId) return notify?.("Open a session first", "warn");
    setBusy(true);
    try {
      const d = await api(`/api/timeline/${encodeURIComponent(sessionId)}`);
      const msgs = (d?.messages || []).map((m) => ({
        ts: m.ts, kind: "message", text: `${m.role}: ${String(m.content || "").slice(0, 90)}`,
      }));
      const traces = (d?.trace_events || []).map((t) => ({
        ts: t.ts, kind: t.kind || "trace", text: String(t.type || t.kind || "event"),
      }));
      setItems([...msgs, ...traces].sort((a, b) => (a.ts || 0) - (b.ts || 0)));
      notify?.(`Timeline loaded (${msgs.length + traces.length} events)`, "ok");
    } catch (e) { notify?.(e.message || String(e), "error"); }
    finally { setBusy(false); }
  }, [sessionId, notify]);

  useEffect(() => { if (sessionId) fromSession(); /* eslint-disable-next-line */ }, [sessionId]);

  const fromText = async () => {
    if (!raw.trim()) return notify?.("Paste timestamped lines (time | event)", "warn");
    setBusy(true);
    try {
      const r = await runSec("timeline", { text: raw });
      const tl = r?.timeline || r?.items || [];
      setItems(tl.map((x) => ({ ts: x.time ? Date.parse(x.time) / 1000 : null, kind: x.phase || "event", text: x.event || JSON.stringify(x) })));
      notify?.("Timeline built", "ok");
      emitXp("hunt_completed");
    } catch (e) { notify?.(e.message || String(e), "error"); }
    finally { setBusy(false); }
  };

  const fmt = (ts) => (ts ? new Date(ts * 1000).toLocaleString() : "—");
  return <div style={{ display: "grid", gap: 10 }}>
    <div style={panel}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
        <div style={{ flex: 1, minWidth: 240 }}>
          <div style={label}>Paste timestamped events (`2026-11-15 12:30 | kerberoasting attempt`)</div>
          <textarea className="input" style={{ ...ta, minHeight: 80 }} value={raw} onChange={(e) => setRaw(e.target.value)} />
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button className="btn sm" onClick={fromText} disabled={busy}>Build</button>
          <button className="btn sm ghost" onClick={fromSession} disabled={busy || !sessionId}><Icon name="history" size={13} /> Session</button>
        </div>
      </div>
    </div>
    <div style={panel}>
      <div className="side-title" style={{ fontSize: 11, marginBottom: 8 }}>Timeline ({items.length})</div>
      {!items.length && <div style={label}>No events yet.</div>}
      <div style={{ display: "grid", gap: 0, maxHeight: 420, overflow: "auto", paddingInlineStart: 4 }}>
        {items.map((it, i) => (
          <div key={i} style={{ display: "grid", gridTemplateColumns: "12px 1fr", gap: 10 }}>
            <div style={{ display: "grid", justifyItems: "center" }}>
              <span style={{ width: 8, height: 8, borderRadius: 999, background: "var(--accent)", boxShadow: "0 0 8px rgba(204,0,0,.6)", marginTop: 10 }} />
              {i < items.length - 1 && <span style={{ width: 1, flex: 1, minHeight: 22, background: "rgba(204,0,0,.25)" }} />}
            </div>
            <div style={{ padding: "6px 0", borderBottom: "1px solid rgba(255,255,255,.04)" }}>
              <div style={{ display: "flex", gap: 8, fontSize: 11, color: "var(--text-2)" }}>
                <span>{fmt(it.ts)}</span><span className="pill" style={{ minHeight: 18, fontSize: 10 }}>{it.kind}</span>
              </div>
              <div style={{ fontSize: 12 }}>{it.text}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  </div>;
}

const TOOL_CHOICES = ["EDR", "SIEM", "NDR", "AV", "WAF", "IDS", "Proxy", "Email Gateway", "DLP", "PAM", "MFA", "Backup", "Vulnerability Scanner", "Sandbox"];

function DefenseTool({ notify }) {
  const [tools, setTools] = useState(["EDR", "SIEM", "AV", "MFA"]);
  const [gaps, setGaps] = useState(null);
  const [hypo, setHypo] = useState("");
  const [plan, setPlan] = useState(null);
  const [query, setQuery] = useState("");
  const [queries, setQueries] = useState(null);
  const [busy, setBusy] = useState(false);

  const toggle = (t) => setTools((cur) => cur.includes(t) ? cur.filter((x) => x !== t) : [...cur, t]);

  const runGaps = async () => {
    setBusy(true);
    try { setGaps(await runSec("defense_gaps", { tools })); notify?.("Gap analysis ready", "ok"); }
    catch (e) { notify?.(e.message || String(e), "error"); }
    finally { setBusy(false); }
  };
  const runHunt = async () => {
    if (!hypo.trim()) return notify?.("Write a hunt hypothesis first", "warn");
    setBusy(true);
    try { setPlan(await runSec("hunt", { hypothesis: hypo })); emitXp("hunt_completed"); notify?.("Hunt plan generated", "ok"); }
    catch (e) { notify?.(e.message || String(e), "error"); }
    finally { setBusy(false); }
  };
  const runQuery = async () => {
    if (!query.trim()) return notify?.("Describe the behaviour to query", "warn");
    setBusy(true);
    try { setQueries(await runSec("query_build", { description: query })); emitXp("intel_lookup"); notify?.("Queries built", "ok"); }
    catch (e) { notify?.(e.message || String(e), "error"); }
    finally { setBusy(false); }
  };

  return <div style={{ display: "grid", gap: 10 }}>
    <div style={panel}>
      <div className="side-title" style={{ fontSize: 11, marginBottom: 8 }}>Deployed controls → defense-in-depth gaps</div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {TOOL_CHOICES.map((t) => (
          <button key={t} className={`btn sm ${tools.includes(t) ? "" : "ghost"}`} onClick={() => toggle(t)}>{t}</button>
        ))}
      </div>
      <div style={{ marginTop: 8 }}><button className="btn sm" onClick={runGaps} disabled={busy}>Analyse gaps</button></div>
      {gaps && <pre style={{ ...pre, marginTop: 8 }}>{JSON.stringify(gaps, null, 2)}</pre>}
    </div>
    <div style={panel}>
      <div className="side-title" style={{ fontSize: 11, marginBottom: 8 }}>Threat hunt plan</div>
      <textarea className="input" style={{ ...ta, minHeight: 70 }} value={hypo} onChange={(e) => setHypo(e.target.value)} placeholder="Hypothesis: an adversary is using Kerberoasting against service accounts…" />
      <div style={{ marginTop: 8 }}><button className="btn sm" onClick={runHunt} disabled={busy}>Build hunt plan</button></div>
      {plan && <pre style={{ ...pre, marginTop: 8 }}>{JSON.stringify(plan, null, 2)}</pre>}
    </div>
    <div style={panel}>
      <div className="side-title" style={{ fontSize: 11, marginBottom: 8 }}>Detection query builder (SPL / KQL / EQL / AQL)</div>
      <textarea className="input" style={{ ...ta, minHeight: 70 }} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Detect encoded PowerShell spawning from Office…" />
      <div style={{ marginTop: 8 }}><button className="btn sm" onClick={runQuery} disabled={busy}>Build queries</button></div>
      {queries && <pre style={{ ...pre, marginTop: 8 }}>{JSON.stringify(queries, null, 2)}</pre>}
    </div>
  </div>;
}

export default function OpsPanel({ notify, sessionId }) {
  const [sub, setSub] = useState("graph");
  const tabs = useMemo(() => [
    { id: "graph", label: "IOC Graph", icon: "graph" },
    { id: "hash", label: "Hash Intel", icon: "search" },
    { id: "timeline", label: "Timeline", icon: "clock" },
    { id: "defense", label: "Defense & Hunt", icon: "shield" },
  ], []);
  return <div style={{ display: "grid", gap: 12 }}>
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
      <div className="side-title" style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 6 }}><Icon name="graph" size={14} /> Operations</div>
      <div style={{ fontSize: 11, color: "var(--text-2)" }}>Graph · Hash · Timeline · Coverage (local CyberOps)</div>
    </div>
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
      {tabs.map((t) => (
        <button key={t.id} className={`btn sm ${sub === t.id ? "" : "ghost"}`} onClick={() => setSub(t.id)}>
          <Icon name={t.icon} size={13} /> {t.label}
        </button>
      ))}
    </div>
    {sub === "graph" && <GraphTool notify={notify} />}
    {sub === "hash" && <HashTool notify={notify} />}
    {sub === "timeline" && <TimelineTool notify={notify} sessionId={sessionId} />}
    {sub === "defense" && <DefenseTool notify={notify} />}
  </div>;
}
