// @ts-nocheck
import React, { useCallback, useEffect, useState } from "react";
import Icon from "./Icon.jsx";
import { t } from "../ui/i18n.js";

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || data.error || `HTTP ${res.status}`);
  return data;
}

export default function ComputerPanel({ notify }) {
  const [providers, setProviders] = useState([]);
  const [computers, setComputers] = useState([]);
  const [active, setActive] = useState(null);
  const [command, setCommand] = useState("uname -a");
  const [output, setOutput] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [p, c] = await Promise.all([
        api("/api/computer/providers"),
        api("/api/computer/computers"),
      ]);
      setProviders(p.providers || []);
      setComputers(c.computers || []);
      setError("");
    } catch (e) { setError(e.message); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const create = async (mode) => {
    try {
      const row = await api("/api/computer/computers", {
        method: "POST", body: JSON.stringify({ mode }),
      });
      setActive(row.id); notify?.(`${mode} computer created`, "ok"); await load();
    } catch (e) { setError(e.message); notify?.(e.message, "error"); }
  };

  const run = async () => {
    if (!active) return;
    try {
      const r = await api(`/api/computer/computers/${active}/execute`, {
        method: "POST", body: JSON.stringify({ command }),
      });
      setOutput(`$ ${command}\n${r.stdout || ""}${r.stderr ? "\n[stderr]\n" + r.stderr : ""}\n[exit ${r.exit_code}]`);
    } catch (e) { setOutput(e.message); }
  };

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div className="ctx-card">
        <h4 style={{ margin: 0 }}>{t("كمبيوتر الذكاء الاصطناعي", "AI Computer")}</h4>
        <div style={{ fontSize: 11, color: "var(--muted)" }}>
          {t("بيئة لينكس حقيقية ومعزولة للوكيل — ليست محاكاة طرفية.", "Real isolated Linux environment for the agent — not a simulated terminal.")}
        </div>
      </div>

      {error && <div className="ctx-card" style={{ color: "var(--err)", whiteSpace: "pre-wrap", fontSize: 11 }}>{error}</div>}

      <div className="ctx-card">
        <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>{t("المزودون", "Providers")}</div>
        {providers.map((p) => (
          <div key={p.name} style={{ fontSize: 11, marginBottom: 4 }}>
            <Icon name={p.configured ? "check" : "alert"} size={12} /> {p.name} — {p.configured ? "configured" : "not configured"} · {p.notes}
          </div>
        ))}
      </div>

      <div className="ctx-card">
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <button className="btn sm primary" onClick={() => create("temporary")}><Icon name="clock" size={12} /> {t("كمبيوتر مؤقت", "Temporary computer")}</button>
          <button className="btn sm ghost" onClick={() => create("persistent")}><Icon name="database" size={12} /> {t("كمبيوتر دائم", "Persistent computer")}</button>
          <button className="btn sm ghost" onClick={load}><Icon name="refresh" size={12} /> {t("تحديث", "Refresh")}</button>
        </div>
        <div style={{ marginTop: 8, fontSize: 11 }}>
          {computers.length ? computers.map((c) => (
            <button key={c.id} className="side-item" onClick={() => setActive(c.id)} style={{ width: "100%", textAlign: "start" }}>
              {c.mode} · {c.provider} · {c.status} · {c.id}
            </button>
          )) : t("لا توجد أجهزة بعد.", "No computers yet.")}
        </div>
      </div>

      {active && (
        <div className="ctx-card">
          <div style={{ fontSize: 12, fontWeight: 600 }}>{t("الطرفية", "Terminal")} · {active}</div>
          <input className="input" value={command} onChange={(e) => setCommand(e.target.value)} />
          <button className="btn sm primary" style={{ marginTop: 6 }} onClick={run}><Icon name="terminal" size={12} /> {t("تنفيذ", "Execute")}</button>
          <pre style={{ whiteSpace: "pre-wrap", maxHeight: 260, overflow: "auto", fontSize: 11 }}>{output}</pre>
        </div>
      )}
    </div>
  );
}
