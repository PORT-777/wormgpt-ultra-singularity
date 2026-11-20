// @ts-nocheck
import React, { useCallback, useEffect, useRef, useState } from "react";
import Icon from "./Icon.jsx";
import { useToast } from "./Toast.jsx";
import { stateView } from "./AsyncState.jsx";
import SessionContextMenu from "./SessionContextMenu.jsx";

async function apiFetch(url, opts = {}, authToken) {
  const headers = { ...(opts.headers || {}) };
  if (authToken) headers.Authorization = `Bearer ${authToken}`;
  const res = await fetch(url, { ...opts, headers });
  let data = null;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) data = await res.json().catch(() => null);
  else data = await res.text().catch(() => null);
  if (!res.ok) {
    const msg = (data && (data.detail || data.error || data.message)) || `HTTP ${res.status}`;
    const err = new Error(String(msg));
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

function usePoll(fn, deps, ms = 5000) {
  useEffect(() => {
    let ok = true;
    const run = async () => { if (ok) await fn(); };
    run();
    const t = setInterval(run, ms);
    return () => { ok = false; clearInterval(t); };
  }, deps); // eslint-disable-line
}

function usePanelState(initial = []) {
  const [data, setData] = useState(initial);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const loaded = useRef(false);
  const setOk = useCallback((v) => { setData(v); setError(""); setLoading(false); loaded.current = true; }, []);
  const setErr = useCallback((e) => { setError(String(e?.message || e || "تعذر تحميل البيانات.")); setLoading(false); }, []);
  const begin = useCallback((silent = false) => { if (!silent && !loaded.current) setLoading(true); }, []);
  return { data, setData, loading, error, setOk, setErr, begin };
}

const H = ({ title, action, children }) => <><div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}><div className="side-title" style={{ fontSize: 12 }}>{title}</div>{action}</div>{children}</>;
const fmtErr = (e) => e?.status ? `${e.message} (HTTP ${e.status})` : String(e?.message || e || "فشل الاتصال بالشبكة.");

function Sessions({ sessionId, onSelectSession, authToken }) {
  const toast = useToast();
  const s = usePanelState([]);
  const [q, setQ] = useState("");
  const [dq, setDq] = useState("");
  const [menu, setMenu] = useState(null); // {session, anchor:{top,left,bottom,right}}
  const [renameId, setRenameId] = useState(null);
  const [renameVal, setRenameVal] = useState("");
  const [confirmDel, setConfirmDel] = useState(null); // session
  const [confirmDelAll, setConfirmDelAll] = useState(false);
  const renameRef = useRef(null);
  const pendingDel = useRef(new Map()); // id -> {timer,snapshot}
  useEffect(()=>{ const t=setTimeout(()=>setDq(q), 220); return ()=>clearTimeout(t); },[q]);
  useEffect(()=>()=>{ pendingDel.current.forEach(v=>clearTimeout(v.timer)); },[]);

  const load = useCallback(async (silent = true) => {
    s.begin(silent);
    try {
      const qs = dq.trim() ? `?q=${encodeURIComponent(dq.trim())}` : "";
      const d = await apiFetch(`/api/history${qs}`, {}, authToken);
      s.setOk(Array.isArray(d) ? d : (d?.sessions || []));
    }
    catch (e) { s.setErr(fmtErr(e)); if (!silent) toast.error(`Sessions: ${fmtErr(e)}`); }
  }, [authToken, dq]); // eslint-disable-line
  usePoll(() => load(true), [authToken, sessionId, dq], 5000);

  const patch = async (id, body, optimistic) => {
    const prev = s.data;
    if (optimistic) s.setOk(optimistic(prev));
    try { const r = await apiFetch(`/api/sessions/${encodeURIComponent(id)}`, { method:"PATCH", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body) }, authToken); await load(false); return r; }
    catch (e) { s.setOk(prev); toast.error(`Update failed: ${fmtErr(e)}`); throw e; }
  };

  const doRename = async (id, title) => {
    const t = (title||"").trim();
    setRenameId(null);
    if (!t) return;
    await patch(id, {title:t}, (prev)=>(prev||[]).map(x=>((x.id||x.session_id)===id?{...x,title:t}:x))).catch(()=>{});
  };

  const doDuplicate = async (item) => {
    const id = item.id || item.session_id;
    const prev = s.data;
    try {
      const r = await apiFetch(`/api/sessions/${encodeURIComponent(id)}/duplicate`, { method:"POST" }, authToken);
      toast.success("Session duplicated.");
      await load(false);
      const nid = r?.session?.id; if (nid) onSelectSession(nid);
    } catch (e) { s.setOk(prev); toast.error(`Duplicate failed: ${fmtErr(e)}`); }
  };

  const doPin = async (item) => {
    const id = item.id || item.session_id;
    const np = !item.pinned;
    await patch(id, {pinned:np}, (prev)=> (prev||[]).map(x=>((x.id||x.session_id)===id?{...x,pinned:np?1:0}:x)).sort((a,b)=>(b.pinned?1:0)-(a.pinned?1:0)||((b.created||0)-(a.created||0)))).catch(()=>{});
  };

  const commitDelete = async (id) => {
    const p = pendingDel.current.get(id); if(!p) return;
    pendingDel.current.delete(id);
    try { await apiFetch(`/api/sessions/${encodeURIComponent(id)}`, { method:"DELETE" }, authToken); }
    catch (e) { if (e?.status !== 404) toast.error(`Delete failed: ${fmtErr(e)}`); }
  };

  const doDelete = async (item) => {
    const id = item.id || item.session_id;
    const prev = s.data || [];
    s.setOk(prev.filter(x => (x.id||x.session_id) !== id));
    if (id === sessionId) onSelectSession("new");
    setConfirmDel(null);
    const timer = setTimeout(()=>commitDelete(id), 6000);
    pendingDel.current.set(id, {timer, snapshot:item});
    toast.info(`Deleted — Undo?`, { duration: 6000, action: { label: "Undo", onClick: async () => {
      const p = pendingDel.current.get(id);
      if (p) { clearTimeout(p.timer); pendingDel.current.delete(id); }
      s.setOk(prev);
      if (id === sessionId) onSelectSession(id);
      toast.success("Session restored.");
    }}});
  };

  const doDeleteAll = async () => {
    setConfirmDelAll(false);
    const prev = s.data || [];
    pendingDel.current.forEach(v => clearTimeout(v.timer));
    pendingDel.current.clear();
    s.setOk([]);
    onSelectSession("new");
    try {
      const r = await apiFetch("/api/sessions", { method: "DELETE" }, authToken);
      toast.success(`تم مسح جميع الجلسات (${r?.sessions ?? prev.length})`);
      await load(false);
    } catch (e) {
      s.setOk(prev);
      toast.error(`فشل مسح الجلسات: ${fmtErr(e)}`);
    }
  };

  const startRename = (item) => { const id=item.id||item.session_id; setRenameId(id); setRenameVal(item.title||id); setTimeout(()=>renameRef.current?.select?.(), 0); };
  const openMenu = (e, item) => { e.stopPropagation(); const r=e.currentTarget.getBoundingClientRect(); setMenu({session:item, anchor:{top:r.top,left:r.left,bottom:r.bottom,right:r.right}}); };
  const onRowKey = (e,id)=>{ if((e.key==="Enter"||e.key===" ") && renameId!==id){ e.preventDefault(); onSelectSession(id);} };

  const localQ = q.trim().toLowerCase();
  const f = (s.data || []).filter((x) => !localQ || JSON.stringify(x).toLowerCase().includes(localQ));
  return <><H title={`Sessions (${(s.data || []).length})`} action={<button className="btn sm ghost" onClick={() => onSelectSession("new")}><Icon name="plus" size={13} />New</button>} />
    <div style={{ position:"relative", marginBottom:8 }}>
      <span style={{ position:"absolute", insetInlineStart:9, top:8, color:"var(--muted)", pointerEvents:"none" }}><Icon name="search" size={13}/></span>
      <input className="input" style={{ paddingInlineStart:30 }} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search sessions..." aria-label="Search sessions" />
    </div>
    {stateView({
      loading: s.loading, error: s.error, empty: !s.loading && !s.error && f.length === 0, onRetry: () => load(false),
      loadingLabel: "Loading sessions...",
      emptyLabel: (q.trim() || (s.data || []).length) ? "No search results." : "No saved sessions yet.",
      emptyHint: (q.trim() || (s.data || []).length) ? "Try a different search." : "Start a new chat.",
      children: <div style={{ display: "grid", gap: 4 }}>{f.map((item) => {
        const id = item.session_id || item.id;
        const active = id === sessionId;
        const editing = renameId === id;
        return <div key={id} className={`list-item session-item ${active ? "active" : ""}`} role="button" tabIndex={0} onClick={() => !editing && onSelectSession(id)} onKeyDown={(e)=>onRowKey(e,id)} title={item.title || id}>
          {item.pinned ? <span className="session-pin" title="Pinned" aria-label="Pinned">📌</span> : <Icon name="chat" size={14} />}
          {editing ? (
            <input ref={renameRef} className="session-rename-input" value={renameVal}
              onClick={(e)=>e.stopPropagation()} onChange={(e)=>setRenameVal(e.target.value)}
              onBlur={()=>doRename(id, renameVal)}
              onKeyDown={(e)=>{ if(e.key==="Enter"){ e.preventDefault(); doRename(id, renameVal); } if(e.key==="Escape"){ e.preventDefault(); setRenameId(null); } }} />
          ) : (
            <span style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.title || id}</span>
          )}
          {!editing && <span className="muted" style={{ fontSize: 10 }}>{item.n ?? ""}</span>}
          {!editing && <button type="button" className="btn sm ghost session-more" aria-label="Session actions" aria-haspopup="menu" title="Actions"
            onClick={(e)=>openMenu(e,item)} onKeyDown={(e)=>{ if(e.key==="Enter"||e.key===" "){ openMenu(e,item); } }}>⋮</button>}
        </div>;
      })}</div>
    })}
    <div className="sidebar-footer" style={{ display:"flex", justifyContent:"space-between", alignItems:"center", gap:8, marginTop:10, paddingTop:10, borderTop:"1px solid rgba(204,0,0,.18)" }}>
      <span className="muted" style={{ fontSize:11 }}>{(s.data || []).length} saved session{(s.data || []).length === 1 ? "" : "s"}</span>
      <button type="button" className="btn sm danger" disabled={!(s.data || []).length} onClick={()=>setConfirmDelAll(true)} title="Delete every saved session permanently">
        <Icon name="trash" size={13} /> مسح جميع الجلسات
      </button>
    </div>
    {confirmDelAll && <div className="overlay" style={{zIndex:1200}} onMouseDown={(e)=>{ if(e.target===e.currentTarget) setConfirmDelAll(false); }}>
      <div className="card" role="dialog" aria-modal="true" aria-label="Delete all sessions" style={{width:"min(460px,92vw)",margin:"12vh auto",padding:16,border:"1px solid rgba(204,0,0,.45)",boxShadow:"0 18px 50px rgba(0,0,0,.55)"}}>
        <div style={{fontWeight:700,marginBottom:6}}>Delete ALL {(s.data || []).length} sessions?</div>
        <div className="muted" style={{fontSize:12,marginBottom:14}}>This permanently removes every session, its messages and its trace events. This action cannot be undone.</div>
        <div className="row" style={{justifyContent:"flex-end",gap:8}}>
          <button className="btn sm ghost" onClick={()=>setConfirmDelAll(false)}>إلغاء</button>
          <button className="btn sm danger" onClick={doDeleteAll}>مسح الكل نهائيًا</button>
        </div>
      </div>
    </div>}
    {menu && <SessionContextMenu anchor={menu.anchor} session={menu.session} onClose={()=>setMenu(null)}
      onRename={startRename} onDuplicate={doDuplicate} onPin={doPin} onDelete={(it)=>setConfirmDel(it)} />}
    {confirmDel && <div className="overlay" style={{zIndex:1200}} onMouseDown={(e)=>{ if(e.target===e.currentTarget) setConfirmDel(null); }}>
      <div className="card" role="dialog" aria-modal="true" aria-label="Delete session" style={{width:"min(420px,92vw)",margin:"12vh auto",padding:16,background:"var(--panel,#121826)",border:"1px solid var(--border,#253046)",boxShadow:"0 18px 50px rgba(0,0,0,.45)"}}>
        <div style={{fontWeight:700,marginBottom:6,color:"var(--text,#e7edf7)"}}>Delete “{confirmDel.title||confirmDel.id}”?</div>
        <div className="muted" style={{fontSize:12,marginBottom:14}}>This removes the session and its messages. You’ll have 6 seconds to undo.</div>
        <div className="row" style={{justifyContent:"flex-end",gap:8}}>
          <button className="btn sm ghost" onClick={()=>setConfirmDel(null)}>Cancel</button>
          <button className="btn sm" style={{background:"#DC2626",color:"#fff",borderColor:"#b91c1c"}} onClick={()=>doDelete(confirmDel)}>Delete</button>
        </div>
      </div>
    </div>}
  </>;
}

function Files({ authToken }) {
  const toast = useToast();
  const s = usePanelState({files:[], root:""});
  const [q, setQ] = useState("");
  const [viewer, setViewer] = useState(null); // {path,content,size,truncated,loading,error,query}
  const [busy, setBusy] = useState("");
  const load = useCallback(async (silent = true) => {
    s.begin(silent);
    try { const d = await apiFetch("/api/files", {}, authToken); const files = Array.isArray(d) ? d : (d?.files || []); s.setOk({files, root: d?.root || ""}); }
    catch (e) { s.setErr(fmtErr(e)); if (!silent) toast.error(`الملفات: ${fmtErr(e)}`); }
  }, [authToken]); // eslint-disable-line
  usePoll(() => load(true), [authToken], 5000);
  useEffect(() => { const h = () => load(true); window.addEventListener("files-changed", h); return () => window.removeEventListener("files-changed", h); }, [load]);

  const upload = async (e) => {
    const f = e.target.files?.[0]; e.target.value = ""; if (!f) return;
    setBusy("upload");
    try {
      const fd = new FormData(); fd.append("file", f);
      await apiFetch("/api/files/upload", { method: "POST", body: fd }, authToken);
      toast.success(`تم رفع الملف: ${f.name}`);
      window.dispatchEvent(new Event("files-changed"));
      load(false);
    } catch (err) { toast.error(`فشل رفع الملف: ${fmtErr(err)}`); }
    finally { setBusy(""); }
  };
  const openFile = async (p) => {
    setViewer({path:p, content:"", loading:true, query:""});
    setBusy(`read:${p}`);
    try {
      const d = await apiFetch(`/api/files/read?path=${encodeURIComponent(p)}`, {}, authToken);
      setViewer(v=>v && v.path===p ? { ...v, loading:false, content: typeof d?.content==="string"?d.content:(d?.content==null?"":JSON.stringify(d.content,null,2)), truncated: !!d?.truncated, path: d?.path||p } : v);
    } catch (err) {
      const msg = fmtErr(err);
      toast.error(`فشلت قراءة الملف: ${msg}`);
      setViewer(v=>v && v.path===p ? { ...v, loading:false, error: msg, content:`Error: ${msg}` } : v);
    } finally { setBusy(""); }
  };
  const del = async (p) => {
    if (!window.confirm(`حذف ${p}?`)) return;
    setBusy(`del:${p}`);
    try { await apiFetch(`/api/files?path=${encodeURIComponent(p)}`, { method: "DELETE" }, authToken); toast.success(`تم حذف الملف: ${p}`); if(viewer?.path===p) setViewer(null); load(false); }
    catch (err) { toast.error(`فشل حذف الملف: ${fmtErr(err)}`); }
    finally { setBusy(""); }
  };
  const copyText = async (text, label="النص") => {
    try { await navigator.clipboard.writeText(text||""); toast.success(`تم نسخ ${label}.`); } catch { toast.error("تعذر النسخ."); }
  };
  const askAbout = (p) => {
    window.dispatchEvent(new CustomEvent("xxxgpt:composer-insert", { detail: { text: `افحص الملف ${p} واشرح محتواه/مشكلته باختصار، واقترح الخطوة التالية.` } }));
    toast.info("تمت إضافة طلب فحص الملف إلى مربع الإرسال.");
  };
  const downloadViewed = () => {
    if(!viewer?.path) return;
    const blob = new Blob([viewer.content||""], {type:"text/plain;charset=utf-8"});
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = (viewer.path.split(/[\\/]/).pop()||"file.txt");
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(a.href), 1000);
  };

  const data = s.data || {files:[], root:""};
  const files = data.files || [];
  const root = data.root || "";
  const ql = q.trim().toLowerCase();
  const f2 = files.filter((f) => !ql || String(f.path || f.name).toLowerCase().includes(ql));
  const viewContent = viewer?.content || "";
  const viewQuery = (viewer?.query||"").trim();
  const viewLines = viewQuery ? viewContent.split(/\r?\n/).filter(l=>l.toLowerCase().includes(viewQuery.toLowerCase())) : null;
  const shown = viewLines ? viewLines.join("\n") : viewContent;

  return <><H title="Files" action={<div className="row"><button className="btn sm ghost" onClick={()=>load(false)} title="تحديث"><Icon name="refresh" size={13}/></button><label className="btn sm ghost" style={{ cursor: "pointer", opacity: busy === "upload" ? .6 : 1 }}><Icon name="upload" size={13} />{busy === "upload" ? "..." : "Upload"}<input type="file" hidden disabled={!!busy} onChange={upload} /></label></div>} />
    {root && <div className="muted" style={{ fontSize: 11, marginBottom: 8, wordBreak: "break-all" }}>{root}</div>}
    <input className="input" style={{ marginBottom: 8 }} value={q} onChange={(e) => setQ(e.target.value)} placeholder="تصفية الملفات..." />
    {stateView({
      loading: s.loading, error: s.error, empty: !s.loading && !s.error && f2.length === 0, onRetry: () => load(false),
      loadingLabel: "جارٍ تحميل الملفات...",
      emptyLabel: files.length ? "لا نتائج للتصفية." : "لا توجد ملفات في مساحة العمل.",
      emptyHint: files.length ? "جرّب اسم ملف مختلف." : "استخدم Upload أو أرفق ملفاً من المحادثة.",
      children: <div style={{ display: "grid", gap: 2 }}>{f2.map((f, i) => {
        const p = f.path || f.name;
        return <div key={`${p}-${i}`} className="list-item" style={{ cursor: f.is_dir ? "default" : "pointer", paddingLeft: 10 + (f.depth || 0) * 12 }} onClick={() => !f.is_dir && openFile(p)} title={p}>
          <Icon name={f.is_dir ? "folder" : "file"} size={14} /><span style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{f.name}</span>
          {!f.is_dir && <span className="muted" style={{fontSize:10}}>{f.size ? `${Math.max(1,Math.round(f.size/1024))}K` : ""}</span>}
          {!f.is_dir && <button type="button" className="btn sm ghost" style={{ minHeight: 20, padding: "0 4px" }} disabled={!!busy} onClick={(e) => { e.stopPropagation(); askAbout(p); }} title="اسأل عنه"><Icon name="chat" size={12} /></button>}
          {!f.is_dir && <button type="button" className="btn sm ghost" style={{ minHeight: 20, padding: "0 4px" }} disabled={!!busy} onClick={(e) => { e.stopPropagation(); del(p); }} title="حذف"><Icon name="trash" size={12} /></button>}
        </div>;
      })}</div>
    })}

    {viewer && <div className="overlay fileview-overlay" onMouseDown={(e)=>{ if(e.target===e.currentTarget) setViewer(null); }}>
      <div className="fileview" role="dialog" aria-modal="true" aria-label={`File viewer: ${viewer.path}`}>
        <div className="fileview-head">
          <div className="fileview-title"><Icon name="file" size={15}/><span title={viewer.path}>{viewer.path}</span>{viewer.truncated && <span className="pill">truncated</span>}</div>
          <div className="row">
            <button className="btn sm ghost" onClick={()=>askAbout(viewer.path)}><Icon name="chat" size={13}/> Ask</button>
            <button className="btn sm ghost" onClick={()=>copyText(viewer.path,"المسار")}><Icon name="copy" size={13}/> Path</button>
            <button className="btn sm ghost" onClick={()=>copyText(viewer.content,"المحتوى")} disabled={viewer.loading}><Icon name="copy" size={13}/> Copy</button>
            <button className="btn sm ghost" onClick={downloadViewed} disabled={viewer.loading}><Icon name="file" size={13}/> Save</button>
            <button className="btn sm ghost" onClick={()=>setViewer(null)} aria-label="إغلاق"><Icon name="close" size={14}/></button>
          </div>
        </div>
        <div className="fileview-tools">
          <input className="input" value={viewer.query||""} onChange={(e)=>setViewer(v=>({...v,query:e.target.value}))} placeholder="ابحث داخل الملف (تصفية السطور)..."/>
          {viewQuery && <span className="muted" style={{fontSize:11}}>{viewLines?.length||0} سطر</span>}
        </div>
        <div className="fileview-body">
          {viewer.loading ? <div className="panel-state"><span className="spinner"/> جارٍ قراءة الملف...</div>
           : viewer.error ? <div className="panel-state error"><div className="title">تعذر فتح الملف</div><div>{viewer.error}</div></div>
           : <pre className="fileview-pre">{shown || <span className="muted">(ملف فارغ)</span>}</pre>}
        </div>
      </div>
    </div>}
  </>;
}

function Memory({ authToken }) {
  const toast = useToast();
  const s = usePanelState([]);
  const [q, setQ] = useState("");
  const [engine, setEngine] = useState("");
  const [busy, setBusy] = useState("");
  const [indexInfo, setIndexInfo] = useState(null);
  const load = useCallback(async (silent = true) => {
    s.begin(silent);
    try {
      const d = await apiFetch(q.trim() ? `/api/memory?q=${encodeURIComponent(q.trim())}` : "/api/memory", {}, authToken);
      s.setOk(d?.items || d?.results || []);
      setEngine(d?.engine || d?.status?.engine || "");
      if (d?.status) setIndexInfo(d.status);
      else {
        try { const st = await apiFetch("/api/memory/status", {}, authToken); setIndexInfo(st || null); } catch {}
      }
    }
    catch (e) { s.setErr(fmtErr(e)); if (!silent) toast.error(`الذاكرة: ${fmtErr(e)}`); }
  }, [q, authToken]); // eslint-disable-line
  usePoll(() => load(true), [q, authToken], 7000);
  const index = async () => {
    setBusy("index");
    try {
      const d = await apiFetch("/api/memory/index", { method: "POST" }, authToken);
      toast.success(`تمت فهرسة مساحة العمل${Number.isFinite(d?.indexed_chunks) ? ` (${d.indexed_chunks} chunk)` : ""}.`);
      if (d?.status) setIndexInfo(d.status);
      load(false);
    }
    catch (e) { toast.error(`فهرسة الذاكرة فشلت: ${fmtErr(e)}`); }
    finally { setBusy(""); }
  };
  const clear = async () => {
    if (!window.confirm("مسح عناصر/فهرس الذاكرة؟")) return;
    setBusy("clear");
    try { await apiFetch("/api/memory", { method: "DELETE" }, authToken); toast.success("تم مسح الذاكرة."); load(false); }
    catch (e) { toast.error(`مسح الذاكرة فشل: ${fmtErr(e)}`); }
    finally { setBusy(""); }
  };
  const lastIndex = indexInfo?.last_index_ts ? new Date(indexInfo.last_index_ts * 1000).toLocaleString() : "—";
  const chunks = Number.isFinite(indexInfo?.indexed_file_chunks) ? indexInfo.indexed_file_chunks : "—";
  return <>
    <H title={`Memory ${engine ? `· ${engine}` : ""}`} action={<div className="row"><button className="btn sm ghost" disabled={!!busy} onClick={index}>{busy === "index" ? "..." : "Index"}</button><button className="btn sm ghost" disabled={!!busy} onClick={clear}>{busy === "clear" ? "..." : "Clear"}</button><button className="btn sm ghost" disabled={s.loading||!!busy} onClick={()=>load(false)}><Icon name="refresh" size={13}/></button></div>} />
    <div className="card" style={{ padding: 10, marginBottom: 8, display: "grid", gap: 4, fontSize: 11 }}>
      <div className="row" style={{ justifyContent: "space-between" }}><span className="muted">Workspace RAG</span><span className={`pill ${indexInfo?.file_index_enabled ? "live" : ""}`}>{indexInfo?.file_index_enabled ? "enabled" : "off"}</span></div>
      <div className="muted">Indexed chunks: <strong style={{ color: "var(--text)" }}>{chunks}</strong> · Last index: <strong style={{ color: "var(--text)" }}>{lastIndex}</strong></div>
      {indexInfo?.error ? <div className="muted" style={{ color: "var(--danger-fg-2)" }}>{indexInfo.error}</div> : null}
    </div>
    <input className="input" style={{ marginBottom: 8 }} value={q} onChange={(e) => setQ(e.target.value)} placeholder="بحث في الذاكرة / RAG" />
    {stateView({
      loading: s.loading, error: s.error, empty: !s.loading && !s.error && (s.data || []).length === 0, onRetry: () => load(false),
      loadingLabel: "جاري تحميل الذاكرة...",
      emptyLabel: q.trim() ? "لا نتائج للبحث في الذاكرة." : "لا توجد عناصر ذاكرة.",
      emptyHint: q.trim() ? "جرّب استعلاماً آخر أو افهرس مساحة العمل." : "استخدم Index لفهرسة ملفات workspace، أو ابدأ محادثات تُنتج ذاكرة.",
      children: <div style={{ display: "grid", gap: 6 }}>{(s.data || []).map((m, i) => <div key={m.id ?? i} className="card quick-card" style={{ padding: 10 }}><div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 4 }}>{m.path || m.kind || m.source || "memory"}</div><div style={{ fontSize: 12, whiteSpace: "pre-wrap" }}>{m.text || m.content || JSON.stringify(m).slice(0, 240)}</div></div>)}</div>
    })}
  </>;
}

function Tasks({ authToken }) {
  const toast = useToast();
  const s = usePanelState([]);
  const [prompt, setPrompt] = useState("");
  const [mins, setMins] = useState(60);
  const [busy, setBusy] = useState("");
  const load = useCallback(async (silent = true) => {
    s.begin(silent);
    try { const d = await apiFetch("/api/tasks", {}, authToken); s.setOk(Array.isArray(d) ? d : (d?.items || d?.tasks || [])); }
    catch (e) { s.setErr(fmtErr(e)); if (!silent) toast.error(`المهام: ${fmtErr(e)}`); }
  }, [authToken]); // eslint-disable-line
  usePoll(() => load(true), [authToken], 8000);
  const add = async () => {
    if (!prompt.trim()) { toast.info("اكتب وصف المهمة أولاً."); return; }
    setBusy("add");
    try { await apiFetch("/api/tasks", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ prompt: prompt.trim(), interval_minutes: Number(mins) || 60 }) }, authToken); toast.success("تم إنشاء المهمة المجدولة."); setPrompt(""); load(false); }
    catch (e) { toast.error(e?.status === 401 ? "تسجيل الدخول مطلوب لإنشاء مهمة." : `إنشاء المهمة فشل: ${fmtErr(e)}`); }
    finally { setBusy(""); }
  };
  const del = async (id) => {
    if (!window.confirm("حذف المهمة المجدولة؟")) return;
    setBusy(`del:${id}`);
    try { await apiFetch(`/api/tasks/${id}`, { method: "DELETE" }, authToken); toast.success("تم حذف المهمة."); load(false); }
    catch (e) { toast.error(`حذف المهمة فشل: ${fmtErr(e)}`); }
    finally { setBusy(""); }
  };
  return <><H title="Tasks / Scheduler" />
    <textarea className="input" style={{ minHeight: 64, resize: "vertical" }} value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="وصف المهمة المجدولة" />
    <div className="row" style={{ margin: "8px 0" }}><input className="input" style={{ width: 90 }} type="number" min={1} value={mins} onChange={(e) => setMins(e.target.value)} /><span className="muted">دقيقة</span><button className="btn sm primary" disabled={busy === "add"} onClick={add}>{busy === "add" ? "..." : "Schedule"}</button></div>
    {stateView({
      loading: s.loading, error: s.error, empty: !s.loading && !s.error && (s.data || []).length === 0, onRetry: () => load(false),
      loadingLabel: "جاري تحميل المهام...",
      emptyLabel: "لا توجد مهام مجدولة.",
      emptyHint: "أضف مهمة دورية وسيقوم backend بتنفيذها حسب الفاصل الزمني.",
      children: <div style={{ display: "grid", gap: 8 }}>{(s.data || []).map((t) => <div key={t.id} className="card quick-card"><div style={{ fontSize: 12, fontWeight: 600 }}>{t.prompt || t.title || t.id}</div><div className="muted" style={{ fontSize: 11 }}>كل {t.interval_minutes} دقيقة</div><button className="btn sm ghost" style={{ marginTop: 8 }} disabled={busy === `del:${t.id}`} onClick={() => del(t.id)}>{busy === `del:${t.id}` ? "..." : "حذف"}</button></div>)}</div>
    })}
  </>;
}

function Proposals({ authToken }) {
  const toast = useToast();
  const s = usePanelState([]);
  const [busy, setBusy] = useState("");
  const load = useCallback(async (silent = true) => {
    s.begin(silent);
    try { const d = await apiFetch("/api/proposals", {}, authToken); s.setOk((Array.isArray(d) ? d : (d?.items || [])).filter((p) => !p.status || p.status === "pending")); }
    catch (e) { s.setErr(fmtErr(e)); if (!silent) toast.error(`المقترحات: ${fmtErr(e)}`); }
  }, [authToken]); // eslint-disable-line
  usePoll(() => load(true), [authToken], 7000);
  const act = async (id, a) => {
    setBusy(`${a}:${id}`);
    try { await apiFetch(`/api/proposals/${id}/${a}`, { method: "POST" }, authToken); toast.success(a === "approve" ? "تم اعتماد المقترح." : "تم رفض المقترح."); load(false); }
    catch (e) { toast.error(e?.status === 401 ? "تسجيل الدخول مطلوب لهذا الإجراء." : `${a === "approve" ? "اعتماد" : "رفض"} المقترح فشل: ${fmtErr(e)}`); }
    finally { setBusy(""); }
  };
  return <><H title="Proposals" />
    {stateView({
      loading: s.loading, error: s.error, empty: !s.loading && !s.error && (s.data || []).length === 0, onRetry: () => load(false),
      loadingLabel: "جاري تحميل المقترحات...",
      emptyLabel: "لا توجد مقترحات معلقة.",
      emptyHint: "المقترحات تظهر هنا عندما ينشئها backend وتنتظر اعتمادك.",
      children: <div style={{ display: "grid", gap: 8 }}>{(s.data || []).map((p) => <div key={p.id} className="card quick-card"><div style={{ fontSize: 12, fontWeight: 600 }}>#{p.id} {p.title}</div>{p.target && <div className="muted" style={{ fontSize: 11 }}>{p.target}</div>}{p.rationale && <div style={{ fontSize: 12, marginTop: 6, whiteSpace: "pre-wrap" }}>{p.rationale}</div>}<div className="row" style={{ marginTop: 8 }}><button className="btn sm primary" disabled={!!busy} onClick={() => act(p.id, "approve")}>{busy === `approve:${p.id}` ? "..." : "Approve"}</button><button className="btn sm" disabled={!!busy} onClick={() => act(p.id, "reject")}>{busy === `reject:${p.id}` ? "..." : "Reject"}</button></div></div>)}</div>
    })}
  </>;
}

function Audit({ authToken }) {
  const toast = useToast();
  const s = usePanelState([]);
  const load = useCallback(async (silent = true) => {
    s.begin(silent);
    try { const d = await apiFetch("/api/audit?limit=80", {}, authToken); s.setOk(Array.isArray(d) ? d : (d?.items || [])); }
    catch (e) { s.setErr(fmtErr(e)); if (!silent) toast.error(`سجل التدقيق: ${fmtErr(e)}`); }
  }, [authToken]); // eslint-disable-line
  usePoll(() => load(true), [authToken], 10000);
  return <><H title="Audit" action={<button className="btn sm ghost" onClick={() => load(false)}><Icon name="refresh" size={13} /></button>} />
    {stateView({
      loading: s.loading, error: s.error, empty: !s.loading && !s.error && (s.data || []).length === 0, onRetry: () => load(false),
      loadingLabel: "جاري تحميل سجل التدقيق...",
      emptyLabel: "لا توجد أحداث تدقيق.",
      emptyHint: "الأحداث تظهر بعد تنفيذ عمليات مسجلة في backend.",
      children: <div style={{ display: "grid", gap: 6 }}>{(s.data || []).map((a, i) => <div key={a.id ?? i} className="card quick-card" style={{ marginBottom: 0, padding: 10 }}><div className="row"><span className="kbd">{a.tool || a.action || "event"}</span></div><div style={{ fontSize: 12, marginTop: 4, whiteSpace: "pre-wrap" }}>{a.detail || a.outcome || JSON.stringify(a).slice(0, 220)}</div></div>)}</div>
    })}
  </>;
}

function Skills({ authToken }) {
  const toast = useToast();
  const s = usePanelState({ count: 0, packs: [] });
  const [q, setQ] = useState("");
  const load = useCallback(async (silent = true) => {
    s.begin(silent);
    try { const d = await apiFetch("/api/skills", {}, authToken); s.setOk({ count: d?.count || 0, packs: d?.packs || [] }); }
    catch (e) { s.setErr(fmtErr(e)); if (!silent) toast.error(`المهارات: ${fmtErr(e)}`); }
  }, [authToken]); // eslint-disable-line
  usePoll(() => load(true), [authToken], 15000);
  const packs = ((s.data?.packs) || []).filter((p) => !q || JSON.stringify(p).toLowerCase().includes(q.toLowerCase())).slice(0, 250);
  return <><H title={`Skills (${s.data?.count || 0})`} action={<button className="btn sm ghost" onClick={() => load(false)}><Icon name="refresh" size={13} /></button>} />
    <input className="input" style={{ marginBottom: 8 }} value={q} onChange={(e) => setQ(e.target.value)} placeholder="بحث في المهارات/الحزم" />
    {stateView({
      loading: s.loading, error: s.error, empty: !s.loading && !s.error && packs.length === 0, onRetry: () => load(false),
      loadingLabel: "جاري تحميل المهارات...",
      emptyLabel: (s.data?.packs || []).length ? "لا نتائج للبحث." : "لا توجد مهارات محملة.",
      emptyHint: (s.data?.packs || []).length ? "جرّب كلمة بحث أخرى." : "تحقق من تحميل backend للحزم أو أعد تشغيله.",
      children: <div style={{ display: "grid", gap: 6 }}>{packs.map((p, i) => <div key={i} className="card quick-card" style={{ marginBottom: 0, padding: 10 }}><div style={{ fontSize: 12, fontWeight: 600 }}>{p.name || p.id || p.path || `pack ${i + 1}`}</div><div className="muted" style={{ fontSize: 11, marginTop: 3, whiteSpace: "pre-wrap" }}>{p.description || p.summary || p.file || ""}</div></div>)}</div>
    })}
  </>;
}

export default function Sidebar({ sessionId, onSelectSession, activeTab, authToken, onOpenSettings, status }) {
  const labels = { sessions: "Sessions", files: "Files", memory: "Memory", tasks: "Tasks", proposals: "Proposals", audit: "Audit", skills: "Skills", gateway: "Gateway", sandbox: "Sandbox", tools: "Security Tools" };
  const providers = Object.values(status?.providers || {});
  return <aside className="side"><div className="side-head"><div className="side-title">{labels[activeTab] || "Workspace"}</div><div className="side-sub">Backend APIs على نفس المصدر · providers {providers.filter((p) => p?.available).length}/{providers.length || 0}</div><div className="side-actions"><button className="btn sm primary" style={{ flex: 1 }} onClick={() => onSelectSession("new")}><Icon name="plus" size={13} /> New session</button><button className="btn sm ghost" onClick={onOpenSettings}><Icon name="settings" size={13} /></button></div></div><div className="side-body">
    {activeTab === "sessions" && <Sessions sessionId={sessionId} onSelectSession={onSelectSession} authToken={authToken} />}
    {activeTab === "files" && <Files authToken={authToken} />}
    {activeTab === "memory" && <Memory authToken={authToken} />}
    {activeTab === "tasks" && <Tasks authToken={authToken} />}
    {activeTab === "proposals" && <Proposals authToken={authToken} />}
    {activeTab === "audit" && <Audit authToken={authToken} />}
    {activeTab === "skills" && <Skills authToken={authToken} />}
      {activeTab === "gateway" && <div className="muted" style={{padding:12}}>Gateway panel is open in the main workspace.</div>}
      {activeTab === "sandbox" && <div className="muted" style={{padding:12}}>Sandbox panel is open in the main workspace (Linux/Windows sessions, command execution, snapshots, results).</div>}
      {activeTab === "tools" && <div className="muted" style={{padding:12}}>Security Tools panel is open in the main workspace (IOC Extractor, YARA, Sigma/Query, MITRE ATT&CK).</div>}
  </div><div style={{ padding: "10px 14px", borderTop: "1px solid var(--border)", fontSize: 11, color: "var(--muted)" }}>Ctrl+, settings · Ctrl+K new · Ctrl+L focus · Esc stop</div></aside>;
}
