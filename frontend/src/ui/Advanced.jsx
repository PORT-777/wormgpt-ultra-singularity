// @ts-nocheck
import React, { useCallback, useEffect, useState } from "react";
import Icon from "../components/Icon.jsx";
import GatewayPanel from "../GatewayPanel.jsx";
import SandboxPanel from "../components/SandboxPanel.jsx";
import ExecPanel from "../components/ExecPanel.jsx";
import SecurityToolsPanel from "../components/SecurityToolsPanel.jsx";
import OpsPanel from "../components/OpsPanel.jsx";
import ProgressPanel from "../components/ProgressPanel.jsx";
import SquadPanel from "../SquadPanel.jsx";
import TraceFeed from "../components/TraceFeed.jsx";
import ConsensusPanel from "../components/ConsensusPanel.jsx";
import WorkspacePanel from "../components/WorkspacePanel.jsx";
import PluginsPanel from "../components/PluginsPanel.jsx";
import { cleanFileList, formatSize } from "./fileUtils.js";
import { t } from "./i18n.js";

const NAV = () => [
  { id: "models", icon: "layers", label: t("الموديلات والمزودون", "Models & providers"), group: "ai" },
  { id: "workspace", icon: "folder", label: t("مدير المساحة", "Workspace Manager"), group: "workspace" },
  { id: "consensus", icon: "layers", label: t("توافق الموديلات", "Model Consensus"), group: "ai" },
  { id: "agents", icon: "bot", label: t("وكلاء الذكاء", "AI Agents"), group: "ai" },
  { id: "activity", icon: "activity", label: t("النشاط والتتبع", "Activity & traces"), group: "ai" },
  { id: "sandbox", icon: "terminal", label: t("الصندوق المعزول", "Sandbox"), group: "workspace" },
  { id: "exec", icon: "code", label: t("بيئة التنفيذ", "Execution"), group: "workspace" },
  { id: "files", icon: "folderOpen", label: t("الملفات", "Files"), group: "workspace" },
  { id: "memory", icon: "brain", label: t("الذاكرة", "Memory"), group: "workspace" },
  { id: "prompts", icon: "bookmark", label: t("البرومبتات المحفوظة", "Saved prompts"), group: "workspace" },
  { id: "tools", icon: "shield", label: t("أدوات الأمان", "Security tools"), group: "advanced" },
  { id: "ops", icon: "graph", label: t("عمليات IOC", "IOC operations"), group: "advanced" },
  { id: "progress", icon: "trophy", label: t("التقدم والخبرة", "Progress & XP"), group: "advanced" },
  { id: "plugins", icon: "plug", label: t("الإضافات والتكاملات", "Plugins & integrations"), group: "advanced" },
  { id: "repos", icon: "gitBranch", label: t("المستودعات المدمجة", "Vendored repos"), group: "advanced" },
  { id: "mcp", icon: "plug", label: t("الإضافات (MCP)", "Extensions (MCP)"), group: "advanced" },
  { id: "export", icon: "download", label: t("تصدير المحادثة", "Export chat"), group: "advanced" },
];

const GROUPS = () => [
  ["ai", t("الذكاء", "AI")],
  ["workspace", t("مساحة العمل", "Workspace")],
  ["advanced", t("متقدم", "Advanced")],
];

function Empty({ children }) { return <div className="ctx-empty" style={{ padding: "40px 12px" }}>{children}</div>; }

function useJson(url, deps = []) {
  const [state, setState] = useState({ loading: true, error: "", data: null });
  const load = useCallback(async () => {
    setState(s => ({ ...s, loading: true, error: "" }));
    try {
      const r = await fetch(url, { cache: "no-store" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setState({ loading: false, error: "", data: await r.json() });
    } catch (e) { setState({ loading: false, error: e.message || "Failed", data: null }); }
  }, [url]); // eslint-disable-line
  useEffect(() => { load(); }, [load, ...deps]);
  return [state, load];
}

function FilesView({ notify }) {
  const [{ loading, error, data }, reload] = useJson("/api/files");
  const [sel, setSel] = useState(null);
  const [content, setContent] = useState("");
  const [q, setQ] = useState("");
  const [showAll, setShowAll] = useState(false);
  const cleaned = cleanFileList(data);
  const all = [...cleaned.dirs, ...cleaned.files];
  const needle = q.trim().toLowerCase();
  const filtered = needle ? all.filter(f => String(f.name || "").toLowerCase().includes(needle)) : all;
  const shown = needle || showAll ? filtered : cleaned.files.slice(0, 200);

  const open = async (f) => {
    const p = f.path || f.name;
    setSel(p); setContent("…");
    try {
      const r = await fetch(`/api/files/read?path=${encodeURIComponent(p)}`);
      const d = await r.json();
      setContent(typeof d.content === "string" ? d.content : JSON.stringify(d.content, null, 2));
    } catch (e) { setContent("Could not read: " + e.message); }
  };

  if (loading) return <Empty>{t("جارٍ تحميل الملفات…", "Loading files…")}</Empty>;
  if (error) return <Empty>{t("الملفات غير متاحة", "Files unavailable")}: {error}</Empty>;
  return (
    <div style={{ display: "grid", gridTemplateColumns: sel ? "260px 1fr" : "1fr", gap: 12, height: "100%" }}>
      <div style={{ minHeight: 0, display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <div className="model-search" style={{ flex: 1 }}>
            <Icon name="search" size={14} />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("ابحث في الملفات…", "Search files…")} />
          </div>
          <button type="button" className="btn sm ghost" onClick={reload} title={t("تحديث", "Refresh")}><Icon name="refresh" size={13} /></button>
        </div>
        <div style={{ fontSize: 11.5, color: "var(--muted)", marginBottom: 6 }}>
          {t(`${all.length} ملفًا`, `${all.length} files`)}
          {cleaned.hidden > 0 ? t(` · ${cleaned.hidden} مخفي (ذاكرة/سجلات)`, ` · ${cleaned.hidden} hidden (caches/logs)`) : ""}
          {needle ? t(` · ${shown.length} نتيجة`, ` · ${shown.length} matches`) : ""}
        </div>
        <div className="ctx-card" style={{ flex: 1, minHeight: 0, overflow: "auto", maxHeight: "none" }}>
          {!shown.length && <Empty>{needle ? t("لا نتائج.", "No matches.") : t("لا ملفات في المساحة.", "No files in the workspace.")}</Empty>}
          {shown.map((f, i) => (
            <button key={`${f.path || f.name}-${i}`} type="button" className="file-row" style={{ width: "100%", background: "transparent", border: 0, cursor: f.is_dir ? "default" : "pointer", textAlign: "start" }} onClick={() => !f.is_dir && open(f)}>
              <Icon name={f.is_dir ? "folder" : "file"} size={13} />
              <span className="nm" title={f.path || f.name}>{f.name}</span>
              {!f.is_dir && <span className="sz">{formatSize(f.size)}</span>}
            </button>
          ))}
          {!needle && !showAll && all.length > 200 && (
            <button type="button" className="mini-btn" style={{ marginTop: 8 }} onClick={() => setShowAll(true)}>
              {t(`عرض كل ${all.length} ملفًا`, `Show all ${all.length} files`)}
            </button>
          )}
        </div>
      </div>
      {sel && (
        <div className="ctx-card" style={{ display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <code style={{ fontSize: 11.5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{sel}</code>
            <span style={{ flex: 1 }} />
            <button type="button" className="mini-btn" onClick={() => setSel(null)}>{t("إغلاق", "Close")}</button>
          </div>
          <pre dir="ltr" style={{ margin: 0, overflow: "auto", background: "var(--code-bg)", border: "1px solid var(--border)", borderRadius: 8, padding: 10, font: "11.5px/1.5 var(--font-mono)", whiteSpace: "pre-wrap" }}>{content}</pre>
        </div>
      )}
    </div>
  );
}

function MemoryView() {
  const [{ loading, error, data }, reload] = useJson("/api/memory?k=30");
  const [profile] = useJson("/api/memory/status");
  if (loading) return <Empty>{t("جارٍ تحميل الذاكرة…", "Loading memory…")}</Empty>;
  if (error) return <Empty>{t("الذاكرة غير متاحة", "Memory unavailable")}: {error}</Empty>;
  const items = data?.items || [];
  const prof = profile.data?.profile || {};
  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div className="ctx-card">
        <h4>{t("المحرك", "Engine")}</h4>
        <div style={{ fontSize: 12.5 }}>{data?.engine || "—"}</div>
        <button type="button" className="btn sm ghost" style={{ marginTop: 8 }} onClick={reload}><Icon name="refresh" size={13} />{t("تحديث", "Refresh")}</button>
      </div>
      <div className="ctx-card">
        <h4>{t("الملف الشخصي", "Profile")}</h4>
        {!Object.keys(prof).length && <Empty>{t("لا يوجد ملف محفوظ.", "No stored profile.")}</Empty>}
        {Object.entries(prof).map(([k, v]) => (
          <div key={k} className="file-row"><span style={{ color: "var(--muted)" }}>{k}</span><span className="nm">{typeof v === "object" ? JSON.stringify(v).slice(0, 160) : String(v).slice(0, 160)}</span></div>
        ))}
      </div>
      <div className="ctx-card">
        <h4>{t(`العناصر الأخيرة (${items.length})`, `Recent items (${items.length})`)}</h4>
        {!items.length && <Empty>{t("لا شيء محفوظ بعد.", "Nothing remembered yet.")}</Empty>}
        {items.map((it, i) => (
          <div key={i} className="file-row" style={{ alignItems: "flex-start" }}>
            <Icon name="brain" size={13} />
            <span className="nm" style={{ whiteSpace: "pre-wrap", lineHeight: 1.5 }}>{String(it.text || it.content || it).slice(0, 500)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function PromptsView({ notify, onUse }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try { const r = await fetch("/api/prompts"); const d = await r.json(); setItems(d.items || []); }
    catch (e) { notify?.(t("البرومبتات", "Prompts") + ": " + e.message, "error"); }
    finally { setLoading(false); }
  }, [notify]);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    if (!title.trim() || !content.trim()) return notify?.(t("العنوان والنص مطلوبان", "Title and content are required"), "warn");
    try {
      const r = await fetch("/api/prompts", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title, content }) });
      if (!r.ok) throw new Error("HTTP " + r.status);
      setTitle(""); setContent(""); notify?.(t("تم حفظ البرومبت", "Prompt saved"), "ok"); load();
    } catch (e) { notify?.(t("فشل الحفظ", "Save failed") + ": " + e.message, "error"); }
  };

  const remove = async (id) => {
    try { await fetch(`/api/prompts/${encodeURIComponent(id)}`, { method: "DELETE" }); load(); }
    catch (e) { notify?.(t("فشل الحذف", "Delete failed") + ": " + e.message, "error"); }
  };

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div className="ctx-card">
        <h4>{t("برومبت جديد", "New prompt")}</h4>
        <input className="input" placeholder={t("العنوان", "Title")} value={title} onChange={(e) => setTitle(e.target.value)} style={{ marginBottom: 8 }} />
        <textarea className="input" placeholder={t("نص البرومبت", "Prompt text")} value={content} onChange={(e) => setContent(e.target.value)} rows={3} style={{ resize: "vertical" }} />
        <button type="button" className="btn sm primary" style={{ marginTop: 8 }} onClick={save}>{t("حفظ البرومبت", "Save prompt")}</button>
      </div>
      <div className="ctx-card">
        <h4>{t(`المكتبة (${items.length})`, `Library (${items.length})`)}</h4>
        {loading && <Empty>{t("جارٍ التحميل…", "Loading…")}</Empty>}
        {!loading && !items.length && <Empty>{t("لا توجد برومبتات محفوظة.", "No saved prompts yet.")}</Empty>}
        {items.map(p => (
          <div key={p.id} className="file-row" style={{ alignItems: "flex-start" }}>
            <div style={{ minWidth: 0, flex: 1 }}>
              <div style={{ fontWeight: 600, fontSize: 12.5 }}>{p.title}</div>
              <div style={{ color: "var(--muted)", fontSize: 11.5, whiteSpace: "pre-wrap" }}>{String(p.content || "").slice(0, 220)}</div>
            </div>
            <button type="button" className="mini-btn" onClick={() => onUse?.(p.content)}>{t("استخدام", "Use")}</button>
            <button type="button" className="mini-btn" onClick={() => remove(p.id)}><Icon name="trash" size={12} /></button>
          </div>
        ))}
      </div>
    </div>
  );
}

function McpView({ notify }) {
  const [st, setSt] = useState(null);
  const [form, setForm] = useState({ name: "", command: "", args: "" });
  const load = useCallback(async () => {
    try { const r = await fetch("/api/mcp"); const d = await r.json(); setSt(d); }
    catch (e) { notify?.(t("MCP", "MCP") + ": " + e.message, "error"); }
  }, [notify]);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    try {
      const r = await fetch("/api/mcp", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: form.name, spec: { command: form.command, args: form.args.split(/\s+/).filter(Boolean) } }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || d.error || "HTTP " + r.status);
      setForm({ name: "", command: "", args: "" }); notify?.(t("تم حفظ خادم MCP", "MCP server saved"), "ok"); load();
    } catch (e) { notify?.(t("فشل الحفظ", "Save failed") + ": " + e.message, "error"); }
  };
  const test = async (name) => {
    try {
      const r = await fetch(`/api/mcp/${encodeURIComponent(name)}/test`, { method: "POST" });
      const d = await r.json();
      notify?.(d.ok ? `${name}: ${d.counts?.tools || 0} ${t("أدوات", "tools")}` : `${name}: ${d.error || t("فشل", "failed")}`, d.ok ? "ok" : "error");
    } catch (e) { notify?.(t("فشل الاختبار", "Test failed") + ": " + e.message, "error"); }
  };
  const remove = async (name) => {
    try { await fetch(`/api/mcp/${encodeURIComponent(name)}`, { method: "DELETE" }); load(); }
    catch (e) { notify?.(t("فشل الحذف", "Delete failed") + ": " + e.message, "error"); }
  };

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div className="ctx-card">
        <h4>{t("الحالة", "Status")}</h4>
        <div style={{ fontSize: 12.5, display: "grid", gap: 4 }}>
          <div>{t("مفعّل", "Enabled")}: <strong>{st?.enabled ? t("نعم", "yes") : t("لا", "no")}</strong></div>
          <div>{t("الحزمة", "SDK")}: <strong>{st?.sdk?.available ? t("مثبّتة", "installed") : t("غير مثبّتة", "not installed")}</strong></div>
          <div>{t("الخوادم", "Servers")}: <strong>{st?.server_count ?? 0}</strong></div>
        </div>
      </div>
      <div className="ctx-card">
        <h4>{t("إضافة خادم stdio", "Add stdio server")}</h4>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
          <input className="input" placeholder={t("الاسم", "name")} value={form.name} onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))} />
          <input className="input" placeholder="command" value={form.command} onChange={(e) => setForm(f => ({ ...f, command: e.target.value }))} />
          <input className="input" placeholder={t("المعطيات (متباعدة بمسافات)", "args (space separated)")} value={form.args} onChange={(e) => setForm(f => ({ ...f, args: e.target.value }))} style={{ gridColumn: "1 / -1" }} />
        </div>
        <button type="button" className="btn sm primary" style={{ marginTop: 8 }} onClick={save}>{t("حفظ الخادم", "Save server")}</button>
      </div>
      <div className="ctx-card">
        <h4>{t("المهيّأ", "Configured")}</h4>
        {!st && <Empty>{t("جارٍ التحميل…", "Loading…")}</Empty>}
        {(st?.servers || []).map(s => (
          <div key={s.name} className="file-row">
            <Icon name="plug" size={13} />
            <span className="nm">{s.name}<span style={{ color: "var(--muted)" }}> · {s.command}</span></span>
            <button type="button" className="mini-btn" onClick={() => test(s.name)}>{t("اختبار", "Test")}</button>
            <button type="button" className="mini-btn" onClick={() => remove(s.name)}><Icon name="trash" size={12} /></button>
          </div>
        ))}
        {st && !st?.servers?.length && <Empty>{t("لا خوادم MCP مهيّأة.", "No MCP servers configured.")}</Empty>}
      </div>
    </div>
  );
}

function VendorView({ notify }) {
  const [{ loading, error, data }, reload] = useJson("/api/vendor/repos");
  const repos = data?.repos || [];
  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div className="ctx-card" style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ flex: 1 }}>
          <h4 style={{ margin: 0 }}>{t("المستودعات المدمجة", "Vendored repos")}</h4>
          <div style={{ fontSize: 11, color: "var(--muted)" }}>
            {data?.vendor_dir || "vendor/"} · {repos.length} repos · {t("متاحة كمراجع للمشروع", "available as project references")}
          </div>
        </div>
        <button type="button" className="btn sm ghost" onClick={reload}>
          <Icon name="refresh" size={12} /> {t("تحديث", "Refresh")}
        </button>
      </div>
      {loading && <Empty>{t("جارٍ تحميل المستودعات…", "Loading repos…")}</Empty>}
      {error && <div className="ctx-card" style={{ color: "var(--danger-fg)" }}>{error}</div>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(260px,1fr))", gap: 10 }}>
        {repos.map((r) => (
          <div key={r.id} className="ctx-card vendor-card" style={{ display: "grid", gap: 7 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="vendor-icon"><Icon name={r.id === "ECC" ? "zap" : r.id === "claude-skills" ? "wand" : r.id === "openhands" ? "bot" : "brain"} size={18} /></span>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{r.name}</div>
                <div style={{ fontSize: 10, color: "var(--muted)" }}>{r.role}</div>
              </div>
            </div>
            <div style={{ fontSize: 10.5, color: "var(--muted)", lineHeight: 1.55 }}>{r.summary || t("لا يوجد ملخص", "No summary")}</div>
            <div style={{ fontSize: 10, color: "var(--muted)" }}>
              {r.present ? `${r.file_count} files · ${r.commit}` : t("غير موجود", "not present")}
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <a className="btn sm ghost" href={r.url} target="_blank" rel="noreferrer">
                <Icon name="globe" size={11} /> GitHub
              </a>
              <button type="button" className="btn sm ghost" onClick={() => { try { navigator.clipboard?.writeText(r.path); notify?.("path copied", "ok"); } catch {} }}>
                <Icon name="copy" size={11} /> {t("المسار", "Path")}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ExportView({ sessionId, notify }) {
  const [state, setState] = useState("");
  const doExport = async () => {
    if (!sessionId) return notify?.(t("لا توجد جلسة محددة", "No session selected"), "warn");
    setState(t("جارٍ التصدير…", "Exporting…"));
    try {
      const r = await fetch(`/api/history/${encodeURIComponent(sessionId)}/export?limit=5000`);
      const d = await r.json();
      const blob = new Blob([JSON.stringify(d, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `port777-${sessionId}.json`;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
      setState(t("تم التنزيل.", "Downloaded."));
      notify?.(t("تم تنزيل التصدير", "Export downloaded"), "ok");
    } catch (e) { setState(t("فشل", "Failed") + ": " + e.message); notify?.(t("فشل التصدير", "Export failed") + ": " + e.message, "error"); }
  };
  return (
    <div className="ctx-card">
      <h4>{t("تصدير المحادثة الحالية", "Export current conversation")}</h4>
      <p style={{ fontSize: 12.5, color: "var(--muted)", marginTop: 0 }}>{t("ينزّل كل الرسائل وأحداث التتبع لهذه الجلسة بصيغة JSON.", "Downloads every message and trace event for this session as JSON.")}</p>
      <code style={{ fontSize: 11.5 }}>{sessionId || t("بدون جلسة", "no session")}</code>
      <div><button type="button" className="btn sm primary" style={{ marginTop: 10 }} onClick={doExport} disabled={!sessionId}>{t("تصدير JSON", "Export JSON")}</button></div>
      {state && <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 8 }}>{state}</div>}
    </div>
  );
}

export default function Advanced({ view, setView, onClose, sessionId, notify, chatModel, setChatModel, trace, toolLogs, planSteps, status, authToken, onAfterRevert, onUsePrompt, execTaskId, onExecTask }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose?.(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const nav = NAV();
  const groups = GROUPS();
  const current = nav.find(n => n.id === view);

  return (
    <div className="adv-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose?.(); }}>
      <div className="adv" role="dialog" aria-modal="true" aria-label={t("مساحة العمل المتقدمة", "Advanced workspace")}>
        <nav className="adv-nav" aria-label={t("الأقسام المتقدمة", "Advanced sections")}>
          <div className="adv-nav-head">
            <div className="brand-mark" style={{ width: 26, height: 26, borderRadius: 8, fontSize: 11 }}>P7</div>
            <div>
              <div className="adv-nav-title">{t("مساحة العمل", "Workspace")}</div>
              <div style={{ fontSize: 10.5, color: "var(--muted)" }}>{t("أدوات متقدمة", "Advanced tools")}</div>
            </div>
          </div>
          {groups.map(([gid, glabel]) => (
            <div key={gid} style={{ marginBottom: 8 }}>
              <div className="side-label">{glabel}</div>
              {nav.filter(n => n.group === gid).map(n => (
                <button key={n.id} type="button" className={`side-item ${view === n.id ? "active" : ""}`} onClick={() => setView(n.id)}>
                  <span className="ico"><Icon name={n.icon} size={16} /></span>{n.label}
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="adv-main">
          <div className="adv-head">
            <span className="adv-title">{current?.label || t("مساحة العمل", "Workspace")}</span>
            <span style={{ flex: 1 }} />
            <button type="button" className="icon-btn" onClick={onClose} title={t("إغلاق", "Close")}><Icon name="close" size={16} /></button>
          </div>

          <div className="adv-body">
            {view === "models" && <GatewayPanel onToast={notify} chatModel={chatModel} onChatModelChange={setChatModel} />}
            {view === "workspace" && <WorkspacePanel open={true} onClose={() => setView("models")} notify={notify} />}
            {view === "consensus" && <ConsensusPanel notify={notify} sessionId={sessionId} />}
            {view === "agents" && <SquadPanel onToast={notify} />}
            {view === "activity" && (
              <div style={{ height: "70vh", border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
                <TraceFeed trace={trace} status={status} planSteps={planSteps} sessionId={sessionId} authToken={authToken} />
              </div>
            )}
            {view === "sandbox" && <SandboxPanel notify={notify} />}
            {view === "exec" && <ExecPanel notify={notify} sessionId={sessionId} initialTaskId={execTaskId} onTaskChange={onExecTask} />}
            {view === "files" && <FilesView notify={notify} />}
            {view === "memory" && <MemoryView />}
            {view === "prompts" && <PromptsView notify={notify} onUse={onUsePrompt} />}
            {view === "tools" && <SecurityToolsPanel notify={notify} />}
            {view === "ops" && <OpsPanel notify={notify} sessionId={sessionId} />}
            {view === "progress" && <ProgressPanel notify={notify} onClose={() => setView("models")} />}
            {view === "plugins" && <PluginsPanel notify={notify} />}
            {view === "mcp" && <McpView notify={notify} />}
      {view === "repos" && <VendorView notify={notify} />}
            {view === "export" && <ExportView sessionId={sessionId} notify={notify} />}
          </div>
        </div>
      </div>
    </div>
  );
}
