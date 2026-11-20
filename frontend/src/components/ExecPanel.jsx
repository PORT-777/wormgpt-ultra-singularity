// @ts-nocheck
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Icon from "./Icon.jsx";
import { formatSize } from "../ui/fileUtils.js";
import { t } from "../ui/i18n.js";

const ENV_ICON = {
  auto: "spark", cloud: "graph", local: "terminal", windows: "terminal",
  linux: "terminal", kali: "shield", wsl: "terminal", android: "terminal",
  sandbox: "lock", upload: "upload", browser: "search",
};

function Badge({ ok, children }) {
  return (
    <span className="tag" style={{
      color: ok ? "var(--accent, #7CFFB2)" : "var(--danger, #ff6b6b)",
      borderColor: "currentColor",
    }}>{children}</span>
  );
}

function Field({ label, value }) {
  return (
    <div className="file-row" style={{ alignItems: "flex-start" }}>
      <span style={{ color: "var(--muted)", minWidth: 130, fontSize: 11.5 }}>{label}</span>
      <span className="nm" style={{ fontSize: 12, wordBreak: "break-word" }}>
        {value === undefined || value === null || value === "" ? "—" : String(value)}
      </span>
    </div>
  );
}

export default function ExecPanel({ notify, sessionId, initialTaskId, onTaskChange }) {
  const [rt, setRt] = useState(null);
  const [caps, setCaps] = useState(null);
  const [envs, setEnvs] = useState([]);
  const [env, setEnv] = useState("auto");
  const [tasks, setTasks] = useState([]);
  const [task, setTask] = useState(null);
  const [busy, setBusy] = useState(false);
  const [cmd, setCmd] = useState("");
  const [code, setCode] = useState("");
  const [files, setFiles] = useState([]);
  const [selFile, setSelFile] = useState(null);
  const [fileBody, setFileBody] = useState("");
  const [tab, setTab] = useState("run");
  const [git, setGit] = useState(null);
  const [gitMsg, setGitMsg] = useState("");
  const pollRef = useRef(null);

  const notifyRef = useRef(notify);
  notifyRef.current = notify;
  const onTaskRef = useRef(onTaskChange);
  onTaskRef.current = onTaskChange;

  const loadRuntime = useCallback(async () => {
    try {
      const r = await fetch("/api/runtime", { cache: "no-store" });
      const d = await r.json();
      setRt(d.summary || null);
      setEnvs(d.environments || []);
    } catch (e) { /* silent: panel shows unavailable */ }
    try {
      const r = await fetch("/api/exec/capabilities", { cache: "no-store" });
      const d = await r.json();
      setCaps(d);
    } catch (e) { /* silent */ }
  }, []);

  const loadTasks = useCallback(async () => {
    try {
      const r = await fetch(`/api/exec/tasks?limit=30${sessionId ? `&session_id=${encodeURIComponent(sessionId)}` : ""}`, { cache: "no-store" });
      const d = await r.json();
      setTasks(d.tasks || []);
    } catch (e) { /* silent */ }
  }, [sessionId]);

  const refreshTask = useCallback(async (tid) => {
    if (!tid) return;
    try {
      const r = await fetch(`/api/exec/tasks/${encodeURIComponent(tid)}`, { cache: "no-store" });
      if (!r.ok) return;
      const d = await r.json();
      const tt = d.task || null;
      setTask(tt);
      onTaskRef.current?.(tt);
      if (tt) {
        const fr = await fetch(`/api/exec/tasks/${encodeURIComponent(tid)}/files`, { cache: "no-store" });
        if (fr.ok) setFiles((await fr.json()).files || []);
      }
    } catch (e) { /* silent */ }
  }, []);

  useEffect(() => { loadRuntime(); loadTasks(); }, [loadRuntime, loadTasks]);

  useEffect(() => {
    if (initialTaskId) refreshTask(initialTaskId);
    // eslint-disable-next-line
  }, [initialTaskId]);

  // Poll a running task until it settles.
  useEffect(() => {
    const st = task?.status;
    if (!task?.id || st === "running" || st === "created") {
      if (pollRef.current) return;
      pollRef.current = setInterval(() => { refreshTask(task?.id); loadTasks(); }, 1200);
    } else if (pollRef.current) {
      clearInterval(pollRef.current); pollRef.current = null;
    }
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
    // eslint-disable-next-line
  }, [task?.id, task?.status, refreshTask, loadTasks]);

  const api = async (url, opts = {}) => {
    const r = await fetch(url, opts);
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d?.detail?.error || d?.detail || d?.error || `HTTP ${r.status}`);
    return d;
  };

  const createTask = async () => {
    setBusy(true);
    try {
      const d = await api("/api/exec/tasks", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ env, session_id: sessionId || null, title: t("مهمة تنفيذ", "execution task") }),
      });
      setTask(d.task); onTaskRef.current?.(d.task);
      notifyRef.current?.(`${t("تم إنشاء مهمة", "Task created")}: ${d.task?.id}`, "ok");
      loadTasks();
    } catch (e) {
      notifyRef.current?.(String(e.message || e), "error");
    } finally { setBusy(false); }
  };

  const runCmd = async () => {
    if (!task?.id || !cmd.trim()) return;
    setBusy(true);
    try {
      const d = await api(`/api/exec/tasks/${task.id}/exec`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: cmd, timeout: 120 }),
      });
      const res = d.result || {};
      if (res.requires_approval) {
        notifyRef.current?.(`${t("الأمر يحتاج موافقة", "Command needs approval")}: ${res.risk} — ${res.reason}`, "warn");
      } else {
        notifyRef.current?.(res.ok ? t("انتهى الأمر بنجاح", "Command succeeded") : `${t("انتهى بكود", "Exited with code")} ${res.exit_code}`, res.ok ? "ok" : "error");
      }
      await refreshTask(task.id);
      loadTasks();
    } catch (e) { notifyRef.current?.(String(e.message || e), "error"); }
    finally { setBusy(false); }
  };

  const runPy = async () => {
    if (!task?.id || !code.trim()) return;
    setBusy(true);
    try {
      const d = await api(`/api/exec/tasks/${task.id}/python`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, timeout: 60 }),
      });
      const res = d.result || {};
      notifyRef.current?.(res.ok ? t("تم تنفيذ بايثون", "Python executed") : `${t("فشل", "failed")} (${res.exit_code})`, res.ok ? "ok" : "error");
      await refreshTask(task.id);
      loadTasks();
    } catch (e) { notifyRef.current?.(String(e.message || e), "error"); }
    finally { setBusy(false); }
  };

  const upload = async (file) => {
    if (!task?.id || !file) return;
    setBusy(true);
    try {
      const fd = new FormData(); fd.append("file", file);
      const r = await fetch(`/api/exec/tasks/${task.id}/import`, { method: "POST", body: fd });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || d?.error || `HTTP ${r.status}`);
      const imp = d.import || {};
      notifyRef.current?.(`${t("تم الاستيراد", "Imported")}: ${imp.files ?? "?"} ${t("ملف", "files")}`, "ok");
      await refreshTask(task.id);
      loadTasks();
    } catch (e) { notifyRef.current?.(String(e.message || e), "error"); }
    finally { setBusy(false); }
  };

  const cancelTask = async () => {
    if (!task?.id) return;
    try {
      await api(`/api/exec/tasks/${task.id}/cancel`, { method: "POST" });
      notifyRef.current?.(t("تم إلغاء المهمة", "Task cancelled"), "ok");
      await refreshTask(task.id);
      loadTasks();
    } catch (e) { notifyRef.current?.(String(e.message || e), "error"); }
  };

  const approve = async () => {
    if (!task?.id) return;
    try {
      await api(`/api/exec/tasks/${task.id}/approve`, { method: "POST" });
      notifyRef.current?.(t("تمت الموافقة", "Approved"), "ok");
      await refreshTask(task.id);
      loadTasks();
    } catch (e) { notifyRef.current?.(String(e.message || e), "error"); }
  };

  const openFile = async (f) => {
    if (!task?.id || f.is_dir) return;
    setSelFile(f.path); setFileBody("…");
    try {
      const d = await api(`/api/exec/tasks/${task.id}/file?path=${encodeURIComponent(f.path)}`);
      setFileBody(d.binary ? t("[ملف ثنائي]", "[binary file]") : (d.content || ""));
    } catch (e) { setFileBody(`ERR: ${e.message}`); }
  };

  const loadGit = useCallback(async (tid) => {
    if (!tid) return;
    try {
      const d = await api(`/api/exec/tasks/${encodeURIComponent(tid)}/git`);
      setGit(d);
    } catch (e) {
      setGit({ error: String(e.message || e) });
    }
  }, []);

  const gitAction = async (action, extra = {}) => {
    if (!task?.id) return;
    setBusy(true);
    try {
      const d = await api(`/api/exec/tasks/${encodeURIComponent(task.id)}/git`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, ...extra }),
      });
      notifyRef.current?.(`${action}: ${d.ok ? "ok" : `exit ${d.code ?? "?"}`}`, d.ok ? "ok" : "warn");
      await loadGit(task.id);
      await refreshTask(task.id);
    } catch (e) { notifyRef.current?.(String(e.message || e), "error"); }
    finally { setBusy(false); }
  };

  const capsList = useMemo(() => (caps?.summary?.capabilities) || {}, [caps]);
  const installed = useMemo(() => (caps?.fingerprint?.tools
    ? Object.entries(caps.fingerprint.tools).filter(([, v]) => v?.installed).map(([k]) => k)
    : []), [caps]);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      {/* Environment fingerprint */}
      <div className="ctx-card">
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <Icon name="terminal" size={16} />
          <h4 style={{ margin: 0 }}>{t("بيئة التنفيذ", "Execution environment")}</h4>
          <span style={{ flex: 1 }} />
          <button type="button" className="mini-btn" onClick={loadRuntime} title={t("إعادة الكشف", "Re-detect")}>
            <Icon name="refresh" size={12} />
          </button>
        </div>
        {rt ? (
          <>
            <Field label={t("النظام", "OS")} value={`${rt.name || ""} ${rt.version || ""}`.trim()} />
            {rt.distro_name && <Field label={t("التوزيعة", "Distribution")} value={`${rt.distro_name} ${rt.distro_version || ""}`.trim()} />}
            <Field label={t("النواة", "Kernel")} value={rt.kernel} />
            <Field label={t("المعمارية", "Architecture")} value={rt.arch} />
            <Field label={t("نوع البيئة", "Runtime")} value={rt.runtime_type} />
            <Field label={t("مساحة العمل", "Workspace")} value={rt.workspace} />
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
              <Badge ok={capsList.process_exec}>{t("تنفيذ أوامر", "shell")}</Badge>
              <Badge ok={capsList.python}>{t("بايثون", "python")}</Badge>
              <Badge ok={capsList.node}>{t("Node", "node")}</Badge>
              <Badge ok={capsList.admin}>{t("صلاحيات مدير", "admin")}</Badge>
              <Badge ok={capsList.kali_security_tools > 0}>{`Kali tools: ${capsList.kali_security_tools || 0}`}</Badge>
              <Badge ok={installed.length > 0}>{`${installed.length} ${t("أداة", "tools")}`}</Badge>
            </div>
            <div style={{ marginTop: 8, fontSize: 11.5, color: "var(--muted)", wordBreak: "break-word" }}>
              {t("أدوات مكتشفة", "Detected tools")}: {installed.join(", ") || "—"}
            </div>
            <div style={{ marginTop: 6, fontSize: 11, color: "var(--muted)" }}>
              {t("هذه بيئة الخادم/المحرك التي تنفّذ فعليًا — وليست جهاز المتصفح. المتصفح وحده لا يستطيع تنفيذ أوامر الجهاز.", "This is the real server/runtime that executes tasks — not the browser/device. A browser alone cannot run device commands.")}
            </div>
          </>
        ) : <div className="ctx-empty">{t("جارٍ الكشف…", "Detecting…")}</div>}
      </div>

      {/* Environment selector */}
      <div className="ctx-card">
        <h4>{t("اختر بيئة التنفيذ", "Choose execution environment")}</h4>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
          {envs.map((e) => (
            <button
              key={e.id}
              type="button"
              className={`mini-btn ${env === e.id ? "primary" : ""}`}
              onClick={() => {
                if (!e.available) {
                  notifyRef.current?.(`${e.label}: ${e.detail || t("غير متاح", "unavailable")}`, "warn");
                  return;
                }
                setEnv(e.id);
              }}
              title={e.detail || e.label}
              style={{ opacity: e.available ? 1 : 0.45 }}
            >
              {e.label}{!e.available ? ` ${t("(غير متاح)", "(n/a)")}` : ""}
            </button>
          ))}
        </div>
        <div style={{ marginTop: 10, display: "flex", gap: 8, alignItems: "center" }}>
          <button type="button" className="btn sm primary" onClick={createTask} disabled={busy}>
            <Icon name="plus" size={13} />{t("مهمة جديدة", "New task")}
          </button>
          {task?.id && (
            <>
              <code style={{ fontSize: 11.5 }}>{task.id}</code>
              <span className="tag">{task.env_label || task.env}</span>
              <span className="tag">{task.status}</span>
              {!task.approved && <button type="button" className="mini-btn" onClick={approve}>{t("موافقة", "Approve")}</button>}
              {task.status === "running" && <button type="button" className="mini-btn" onClick={cancelTask}><Icon name="stop" size={12} />{t("إلغاء", "Cancel")}</button>}
            </>
          )}
        </div>
      </div>

      {task?.id && (
        <div className="ctx-card">
          <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
            {[
              ["run", t("تنفيذ", "Run"), "terminal"],
              ["files", t("الملفات", "Files"), "folder"],
              ["git", "Git", "gitBranch"],
              ["log", t("السجل", "Log"), "activity"],
            ].map(([id, label, ic]) => (
              <button key={id} type="button" className={`mini-btn ${tab === id ? "primary" : ""}`} onClick={() => { setTab(id); if (id === "git") loadGit(task.id); }}>
                <Icon name={ic} size={12} />{label}
              </button>
            ))}
            <span style={{ flex: 1 }} />
            <a className="mini-btn" href={`/api/exec/tasks/${task.id}/archive`} target="_blank" rel="noreferrer">
              <Icon name="download" size={12} />{t("تنزيل ZIP", "Download ZIP")}
            </a>
          </div>

          {tab === "run" && (
            <div style={{ display: "grid", gap: 10 }}>
              <div>
                <div style={{ fontSize: 11.5, color: "var(--muted)", marginBottom: 4 }}>{t("أمر", "Command")}</div>
                <div style={{ display: "flex", gap: 6 }}>
                  <input className="input" dir="ltr" value={cmd} onChange={(e) => setCmd(e.target.value)}
                    placeholder={rt?.family === "windows" ? "Get-ChildItem" : "ls -la"}
                    onKeyDown={(e) => { if (e.key === "Enter") runCmd(); }} style={{ flex: 1, fontFamily: "var(--font-mono)" }} />
                  <button type="button" className="btn sm primary" onClick={runCmd} disabled={busy || !cmd.trim()}>
                    <Icon name="terminal" size={13} />{t("تنفيذ", "Run")}
                  </button>
                </div>
              </div>
              <div>
                <div style={{ fontSize: 11.5, color: "var(--muted)", marginBottom: 4 }}>{t("بايثون", "Python")}</div>
                <textarea className="input" dir="ltr" rows={3} value={code} onChange={(e) => setCode(e.target.value)}
                  placeholder={"print(2 + 2)"} style={{ fontFamily: "var(--font-mono)", resize: "vertical" }} />
                <button type="button" className="btn sm" onClick={runPy} disabled={busy || !code.trim()} style={{ marginTop: 6 }}>
                  <Icon name="code" size={13} />{t("تشغيل بايثون", "Run Python")}
                </button>
              </div>
              <div>
                <div style={{ fontSize: 11.5, color: "var(--muted)", marginBottom: 4 }}>{t("استيراد مشروع (ZIP)", "Import project (ZIP)")}</div>
                <input type="file" accept=".zip,.tar,.gz,.tgz" className="input" style={{ padding: 4 }}
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); e.target.value = ""; }} />
              </div>
            </div>
          )}

          {tab === "files" && (
            <div style={{ display: "grid", gridTemplateColumns: selFile ? "240px 1fr" : "1fr", gap: 10 }}>
              <div style={{ maxHeight: 320, overflow: "auto" }}>
                {files.length === 0 && <div className="ctx-empty">{t("لا ملفات.", "No files.")}</div>}
                {files.map((f, i) => (
                  <button key={`${f.path}-${i}`} type="button" className="file-row"
                    style={{ width: "100%", background: "transparent", border: 0, cursor: f.is_dir ? "default" : "pointer", textAlign: "start" }}
                    onClick={() => !f.is_dir && openFile(f)}>
                    <Icon name={f.is_dir ? "folder" : "file"} size={13} />
                    <span className="nm">{f.path}</span>
                    {!f.is_dir && <span className="sz">{formatSize(f.size)}</span>}
                  </button>
                ))}
              </div>
              {selFile && (
                <div style={{ display: "flex", flexDirection: "column", minHeight: 0 }}>
                  <div style={{ display: "flex", gap: 6, marginBottom: 6, alignItems: "center" }}>
                    <code style={{ fontSize: 11.5, flex: 1, overflow: "hidden", textOverflow: "ellipsis" }}>{selFile}</code>
                    <a className="mini-btn" href={`/api/exec/tasks/${task.id}/download?path=${encodeURIComponent(selFile)}`}>
                      <Icon name="download" size={12} />
                    </a>
                    <button type="button" className="mini-btn" onClick={() => { setSelFile(null); setFileBody(""); }}>×</button>
                  </div>
                  <pre dir="ltr" style={{ margin: 0, overflow: "auto", maxHeight: 300, background: "var(--code-bg)", border: "1px solid var(--border)", borderRadius: 8, padding: 10, font: "11.5px/1.5 var(--font-mono)", whiteSpace: "pre-wrap" }}>{fileBody}</pre>
                </div>
              )}
            </div>
          )}

          {tab === "git" && (
            <div style={{ display: "grid", gap: 8 }}>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
                <button type="button" className="btn sm" onClick={() => loadGit(task.id)}>
                  <Icon name="refresh" size={12} />{t("تحديث", "Refresh")}
                </button>
                <button type="button" className="btn sm" onClick={() => gitAction("init")} disabled={busy}>
                  <Icon name="plus" size={12} />git init
                </button>
                <button type="button" className="btn sm" onClick={() => gitAction("add")} disabled={busy}>
                  <Icon name="plus" size={12} />{t("إضافة الكل", "Add all")}
                </button>
                <input className="input" dir="auto" value={gitMsg} onChange={(e) => setGitMsg(e.target.value)}
                  placeholder={t("رسالة الالتزام", "commit message")} style={{ flex: 1, minWidth: 160 }} />
                <button type="button" className="btn sm primary" disabled={busy || !gitMsg.trim()}
                  onClick={async () => { await gitAction("add"); await gitAction("commit", { message: gitMsg }); setGitMsg(""); }}>
                  <Icon name="check" size={12} />{t("التزام", "Commit")}
                </button>
                <button type="button" className="btn sm" onClick={() => gitAction("diff")} disabled={busy}>diff</button>
                <button type="button" className="btn sm" onClick={() => gitAction("log")} disabled={busy}>log</button>
              </div>
              {git?.error && <div style={{ color: "var(--danger)", fontSize: 12 }}>{git.error}</div>}
              {git?.status && (
                <div>
                  <div style={{ fontSize: 11.5, color: "var(--muted)", marginBottom: 3 }}>status</div>
                  <pre dir="ltr" style={{ margin: 0, overflow: "auto", maxHeight: 160, background: "var(--code-bg)", border: "1px solid var(--border)", borderRadius: 8, padding: 8, font: "11.5px/1.5 var(--font-mono)", whiteSpace: "pre-wrap" }}>{git.status.output || "clean"}</pre>
                </div>
              )}
              {git?.branches && (
                <div>
                  <div style={{ fontSize: 11.5, color: "var(--muted)", marginBottom: 3 }}>branches</div>
                  <pre dir="ltr" style={{ margin: 0, overflow: "auto", maxHeight: 120, background: "var(--code-bg)", border: "1px solid var(--border)", borderRadius: 8, padding: 8, font: "11.5px/1.5 var(--font-mono)", whiteSpace: "pre-wrap" }}>{git.branches.output || "—"}</pre>
                </div>
              )}
              {git?.log && (
                <div>
                  <div style={{ fontSize: 11.5, color: "var(--muted)", marginBottom: 3 }}>log</div>
                  <pre dir="ltr" style={{ margin: 0, overflow: "auto", maxHeight: 180, background: "var(--code-bg)", border: "1px solid var(--border)", borderRadius: 8, padding: 8, font: "11.5px/1.5 var(--font-mono)", whiteSpace: "pre-wrap" }}>{git.log.output || "—"}</pre>
                </div>
              )}
            </div>
          )}

          {tab === "log" && (
            <div style={{ maxHeight: 360, overflow: "auto" }}>
              {(!task.events || !task.events.length) && <div className="ctx-empty">{t("لا أحداث.", "No events.")}</div>}
              {(task.events || []).slice(-120).map((ev, i) => (
                <div key={i} className="file-row" style={{ alignItems: "flex-start", fontSize: 11.5 }}>
                  <span style={{ color: "var(--muted)", minWidth: 64, fontFamily: "var(--font-mono)" }}>
                    {ev.ts ? new Date(ev.ts * 1000).toLocaleTimeString() : ""}
                  </span>
                  <span style={{ minWidth: 96, color: "var(--accent)" }}>{ev.kind}</span>
                  <span className="nm" style={{ whiteSpace: "pre-wrap" }}>{ev.message || ""}</span>
                </div>
              ))}
            </div>
          )}

          {task.result && (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 11.5, color: "var(--muted)", marginBottom: 4 }}>
                {t("آخر ناتج", "Last output")} · exit {task.result.exit_code}
              </div>
              <pre dir="ltr" style={{ margin: 0, overflow: "auto", maxHeight: 220, background: "var(--code-bg)", border: "1px solid var(--border)", borderRadius: 8, padding: 10, font: "11.5px/1.5 var(--font-mono)", whiteSpace: "pre-wrap" }}>
                {(task.result.stdout || "") + (task.result.stderr ? `\n--- stderr ---\n${task.result.stderr}` : "")}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Task history */}
      <div className="ctx-card">
        <h4>{t("المهام", "Tasks")} ({tasks.length})</h4>
        {!tasks.length && <div className="ctx-empty">{t("لا مهام بعد.", "No tasks yet.")}</div>}
        {tasks.slice(0, 15).map((t2) => (
          <div key={t2.id} className="file-row">
            <Icon name="terminal" size={13} />
            <span className="nm" style={{ cursor: "pointer" }} onClick={() => refreshTask(t2.id)}>
              {t2.title || t2.id}
              <span style={{ color: "var(--muted)" }}> · {t2.env_label || t2.env} · {t2.status}</span>
            </span>
            <button type="button" className="mini-btn" onClick={() => refreshTask(t2.id)}>{t("فتح", "Open")}</button>
          </div>
        ))}
      </div>
    </div>
  );
}