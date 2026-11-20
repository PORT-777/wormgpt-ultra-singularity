// @ts-nocheck
import React, { useCallback, useEffect, useState } from "react";
import Icon from "../components/Icon.jsx";
import { t } from "./i18n.js";
import { cleanFileList } from "./fileUtils.js";

const TABS = [
  ["overview", t("نظرة عامة", "Overview")],
  ["activity", t("النشاط", "Activity")],
  ["files", t("الملفات", "Files")],
  ["memory", t("الذاكرة", "Memory")],
];

function fmtTime(ts) {
  const n = Number(ts);
  if (!n) return "";
  const d = new Date(n < 1e12 ? n * 1000 : n);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function ContextPanel({ open, onClose, tab, setTab, planSteps = [], trace = [], toolLogs = [], messages = [], sessionId, attachments = [], status, toast }) {
  const [files, setFiles] = useState({ loading: true, error: "", list: [], root: "" });
  const [mem, setMem] = useState({ loading: true, error: "", engine: "", items: [], profile: null });

  const loadFiles = useCallback(async () => {
    setFiles(f => ({ ...f, loading: true, error: "" }));
    try {
      const r = await fetch("/api/files", { cache: "no-store" });
      const d = await r.json();
      setFiles({ loading: false, error: "", list: Array.isArray(d) ? d : (d.files || []), root: d.root || "" });
    } catch (e) {
      setFiles({ loading: false, error: e.message || "Failed", list: [], root: "" });
    }
  }, []);

  const loadMem = useCallback(async () => {
    setMem(f => ({ ...f, loading: true, error: "" }));
    try {
      const r = await fetch("/api/memory?k=8", { cache: "no-store" });
      const d = await r.json();
      let profile = null;
      try { const p = await fetch("/api/memory/status", { cache: "no-store" }); if (p.ok) profile = (await p.json())?.profile || null; } catch {}
      setMem({ loading: false, error: "", engine: d.engine || "", items: d.items || [], profile });
    } catch (e) {
      setMem({ loading: false, error: e.message || "Failed", engine: "", items: [], profile: null });
    }
  }, []);

  useEffect(() => { if (!open) return; if (tab === "files") loadFiles(); if (tab === "memory") loadMem(); }, [open, tab, loadFiles, loadMem]);

  if (!open) return null;

  const objective = (messages.find(m => m.role === "user")?.content || "").slice(0, 220);
  const done = planSteps.filter(s => s.state === "done").length;
  const runningStep = planSteps.find(s => s.state === "running");
  const recentTrace = trace.filter(t => t && t.kind !== "stream").slice(-60).reverse();
  const cleaned = cleanFileList(files.list);
  const filesArr = cleaned.files.slice(0, 40);

  return (
    <aside className="context2" aria-label="Context panel">
      <div className="ctx-head">
        <span className="ctx-title">{t("التفاصيل", "Details")}</span>
        <span style={{ flex: 1 }} />
        <button type="button" className="icon-btn" title={t("إغلاق اللوحة", "Close panel")} onClick={onClose}><Icon name="close" size={15} /></button>
      </div>

      <div className="ctx-tabs" role="tablist">
        {TABS.map(([id, label]) => (
          <button key={id} type="button" role="tab" aria-selected={tab === id} className={`ctx-tab ${tab === id ? "active" : ""}`} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </div>

      <div className="ctx-body">
        {tab === "overview" && (
          <>
            <div className="ctx-card">
              <h4>{t("الهدف", "Objective")}</h4>
              <div style={{ fontSize: 12.5, color: objective ? "var(--text-2)" : "var(--muted)", whiteSpace: "pre-wrap" }}>
                {objective || t("لا توجد مهمة بعد — أرسل رسالة للبدء.", "No task yet — send a message to get started.")}
              </div>
            </div>

            <div className="ctx-card">
              <h4>{t("التقدم", "Progress")}</h4>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <div className="xp-track" style={{ width: "100%", height: 6 }}><i style={{ width: `${planSteps.length ? (done / planSteps.length) * 100 : 0}%` }} /></div>
                <span style={{ fontSize: 11, color: "var(--muted)", whiteSpace: "nowrap" }}>{done}/{planSteps.length || 0}</span>
              </div>
              {planSteps.map((s, i) => (
                <div key={s.id ?? i} className={`plan-step ${s.state || "pending"}`}>
                  <span className="st">{s.state === "done" ? "✓" : s.state === "failed" ? "!" : (i + 1)}</span>
                  <span>{s.title || s.id || `Step ${i + 1}`}</span>
                </div>
              ))}
              {!planSteps.length && <div style={{ fontSize: 12, color: "var(--muted)" }}>{runningStep ? t("جارٍ التخطيط…", "Planning…") : t("تظهر الخطة هنا للمهام متعددة الخطوات.", "The plan appears here for multi-step tasks.")}</div>}
            </div>

            <div className="ctx-card">
              <h4>{t("الجلسة", "Session")}</h4>
              <div style={{ display: "grid", gap: 5, fontSize: 12, color: "var(--text-2)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}><span>ID</span><code style={{ fontSize: 11 }}>{sessionId || "—"}</code></div>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}><span>{t("الحالة", "Status")}</span><span>{status?.state || "idle"}</span></div>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}><span>{t("الرسائل", "Messages")}</span><span>{messages.length}</span></div>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}><span>{t("المخرجات", "Artifacts")}</span><span>{filesArr.length}</span></div>
              </div>
            </div>
          </>
        )}

        {tab === "activity" && (
          <>
            <div className="ctx-card">
              <h4>{t("النشاط الحي", "Live activity")}</h4>
              {!recentTrace.length && !toolLogs.length && <div className="ctx-empty">Tool calls and agent steps will stream here. Normal chat stays clean.</div>}
              {recentTrace.map((t, i) => (
                <div className="act-row" key={`${t.seq || i}-${i}`}>
                  <div className="act-kind">{t.kind || "event"}{t.tool ? ` · ${t.tool}` : ""}{t.ts ? ` · ${fmtTime(t.ts)}` : ""}</div>
                  <div className="act-text">{String(t.text || "").slice(0, 1200)}</div>
                </div>
              ))}
              {!recentTrace.length && !!toolLogs.length && (
                <div className="act-text">{toolLogs.slice(-40).join("\n")}</div>
              )}
            </div>
          </>
        )}

        {tab === "files" && (
          <>
            <div className="ctx-card">
              <h4>{t("المرفقات", "Attached")}</h4>
              {!attachments.length && <div className="ctx-empty">No files attached to the next message.</div>}
              {attachments.map((a, i) => (
                <div className="file-row" key={`${a.name}-${i}`}>
                  <Icon name={a.ok ? "file" : "alert"} size={13} />
                  <span className="nm">{a.name}</span>
                  <span className="sz">{a.ok ? "ready" : "failed"}</span>
                </div>
              ))}
            </div>
            <div className="ctx-card">
              <h4>{t("ملفات المساحة", "Workspace files")} {files.root ? <span style={{ fontWeight: 400, textTransform: "none", letterSpacing: 0 }}> · {files.root}</span> : null}</h4>
              {files.loading && <div className="ctx-empty">Loading files…</div>}
              {files.error && <div className="ctx-empty">Could not load files: {files.error}</div>}
              {!files.loading && !files.error && !filesArr.length && <div className="ctx-empty">No files in the workspace.</div>}
              {filesArr.map((f, i) => (
                <div className="file-row" key={`${f.path || f.name}-${i}`}>
                  <Icon name="file" size={13} />
                  <span className="nm" title={f.path || f.name}>{f.name}</span>
                  <span className="sz">{f.size ? `${Math.max(1, Math.round(f.size / 1024))}K` : ""}</span>
                </div>
              ))}
              {!!filesArr.length && <button type="button" className="mini-btn" style={{ marginTop: 6 }} onClick={loadFiles}><Icon name="refresh" size={12} />Refresh</button>}
            </div>
          </>
        )}

        {tab === "memory" && (
          <>
            <div className="ctx-card">
              <h4>{t("محرك الذاكرة", "Memory engine")}</h4>
              {mem.loading && <div className="ctx-empty">Loading memory…</div>}
              {mem.error && <div className="ctx-empty">Memory unavailable: {mem.error}</div>}
              {!mem.loading && !mem.error && (
                <div style={{ display: "grid", gap: 6, fontSize: 12, color: "var(--text-2)" }}>
                  <div>{t("المحرك", "Engine")}: <strong>{mem.engine || "—"}</strong></div>
                  {mem.profile && Object.keys(mem.profile).length > 0 && (
                    <div style={{ borderTop: "1px dashed var(--border)", paddingTop: 6 }}>
                      {Object.entries(mem.profile).slice(0, 12).map(([k, v]) => (
                        <div key={k} style={{ display: "flex", gap: 8, justifyContent: "space-between" }}>
                          <span style={{ color: "var(--muted)" }}>{k}</span>
                          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 170 }}>{typeof v === "object" ? JSON.stringify(v).slice(0, 80) : String(v).slice(0, 80)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="ctx-card">
              <h4>{t("أحدث الاستدعاءات", "Recent recall")}</h4>
              {mem.items.slice(0, 12).map((it, i) => (
                <div className="file-row" key={i} style={{ alignItems: "flex-start" }}>
                  <Icon name="brain" size={13} />
                  <span className="nm" style={{ whiteSpace: "pre-wrap", fontSize: 11.5, lineHeight: 1.5 }}>{String(it.text || it.content || it).slice(0, 240)}</span>
                </div>
              ))}
              {!mem.loading && !mem.error && !mem.items.length && <div className="ctx-empty">Nothing remembered yet.</div>}
            </div>
          </>
        )}
      </div>
    </aside>
  );
}