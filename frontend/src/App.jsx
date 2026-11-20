// @ts-nocheck
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Icon from "./components/Icon.jsx";
import Markdown from "./components/Markdown.jsx";
import TracePanel from "./components/TraceFeed.jsx";
import Terminal from "./components/Terminal.jsx";
import VoiceButton from "./components/VoiceButton.jsx";
import Settings from "./components/Settings.jsx";
import CommandPalette from "./components/CommandPalette.jsx";
import ModePicker, { MODE_IDS, MODE_PLACEHOLDERS } from "./components/ModePicker.jsx";
import { useToast } from "./components/Toast.jsx";
import WorkspacePanel from "./components/WorkspacePanel.jsx";
import GatewayPanel from "./GatewayPanel.jsx";
import SandboxPanel from "./components/SandboxPanel.jsx";
import SecurityToolsPanel from "./components/SecurityToolsPanel.jsx";
import ModelPicker from "./ModelPicker.jsx";
import XPBar from "./components/XPBar.jsx";
import OpsPanel from "./components/OpsPanel.jsx";
import ProgressPanel from "./components/ProgressPanel.jsx";
import { emitXp } from "./gamification.js";
import { CheckpointChips, useCheckpoints } from "./components/CheckpointUI.jsx";
import Sidebar from "./ui/Sidebar.jsx";
import Composer from "./ui/Composer.jsx";
import ModelMenu from "./ui/ModelMenu.jsx";
import Welcome from "./ui/Welcome.jsx";
import Message from "./ui/Message.jsx";
import ContextPanel from "./ui/ContextPanel.jsx";
const Advanced = React.lazy(() => import("./ui/Advanced.jsx"));
import ReasoningDashboard from "./components/ReasoningDashboard.jsx";
import { setUiLang, t } from "./ui/i18n.js";

const ROUTES = ["auto"];
const TABS = [
  {id:"sessions",icon:"chat",label:"Sessions"},
  {id:"workspace",icon:"folder",label:"Workspace"},
  {id:"gateway",icon:"shield",label:"Gateway"},
  {id:"sandbox",icon:"terminal",label:"Sandbox"},
  {id:"tools",icon:"activity",label:"Tools"},
  {id:"ops",icon:"graph",label:"Ops"},
  {id:"plugins",icon:"plug",label:"Plugins"},
  {id:"progress",icon:"trophy",label:"Progress"},
];
const PREFS_KEY = "xxxgpt_ui_prefs_v1";
const BACKOFF = [1000,2000,4000,8000,8000];
const readPrefs = () => { try { const p = JSON.parse(localStorage.getItem(PREFS_KEY) || "{}"); return p && typeof p === "object" ? p : {}; } catch { return {}; } };
const pick = (v, allowed, fallback) => allowed.includes(v) ? v : fallback;

class SessionErrorBoundary extends React.Component {
  constructor(props){ super(props); this.state={err:null}; }
  static getDerivedStateFromError(err){ return { err }; }
  componentDidCatch(err, info){ try{ console.error("[SessionRender]", err, info); }catch{} }
  render(){
    if(this.state.err){
      const msg = String(this.state.err?.message || this.state.err || "Render error");
      if(this.props.inline) return <div className="panel-state error" style={{margin:0}}><div className="title">Unable to display message</div><div className="muted" style={{fontSize:12}}>{msg}</div></div>;
      return <div className="panel-state error" style={{margin:"18px auto",maxWidth:560,display:"grid",gap:10}}><div className="title">Session render error</div><div className="muted" style={{fontSize:12,whiteSpace:"pre-wrap"}}>{msg}</div><div className="row"><button className="btn sm" onClick={()=>{ this.setState({err:null}); this.props.onRetry?.(); }}>إعادة المحاولة</button><button className="btn sm ghost" onClick={()=>this.props.onNew?.()}>رجوع للجلسات</button></div></div>;
    }
    return this.props.children;
  }
}

export default function App(){
  const toast = useToast();
  const notify = useCallback((msg, kind="info") => { const m=String(msg??""); if(kind==="error"||kind==="warn") return toast.error(m); if(kind==="ok"||kind==="success") return toast.success(m); return toast.info(m); }, [toast]);
  const initPrefs = useMemo(readPrefs, []);
  const [sessionId,setSessionId]=useState(null);
  const [messages,setMessages]=useState([]);
  const [trace,setTrace]=useState([]);
  const [toolLogs,setToolLogs]=useState([]);
  const [planSteps,setPlanSteps]=useState([]);
  const [status,setStatus]=useState({state:"sleeping",route:"auto",providers:{}});
  const [reasoningLevel,setReasoningLevel]=useState(null);
  const [confidenceScore,setConfidenceScore]=useState(null);
  const [critiqueNotes,setCritiqueNotes]=useState("");
  const [input,setInput]=useState("");
  const [enhancing,setEnhancing]=useState(false);
  const [route,setRoute]=useState(()=>pick(initPrefs.route,ROUTES,"auto"));
  const [chatModel,setChatModel]=useState(()=>{
    const m = String(initPrefs.model || "auto/free").trim();
    return (m === "auto/coding:free" || !m) ? "auto/free" : m;
  });
  const [composerMode,setComposerMode]=useState(()=>pick(initPrefs.mode,MODE_IDS,"code"));
  const [execEnv,setExecEnv]=useState(()=>String(initPrefs.execEnv||"off"));
  const [execEnvs,setExecEnvs]=useState([]);
  const [runtimeInfo,setRuntimeInfo]=useState(null);
  const [execTask,setExecTask]=useState(null);
  const [execArtifacts,setExecArtifacts]=useState([]);
  const [running,setRunning]=useState(false);
  const [fullAccess,setFullAccess]=useState(false);
  const [streamText,setStreamText]=useState("");
  const [authRequired,setAuthRequired]=useState(false);
  const [authToken,setAuthToken]=useState(()=>localStorage.getItem("🔥😈 PORT 777 EVIL ☠️🔥👹_token"));
  const [projectPath,setProjectPath]=useState(()=>localStorage.getItem("port777_project")||"");
  const [projectInput,setProjectInput]=useState(()=>localStorage.getItem("port777_project")||"");
  const [projectWorkspaces,setProjectWorkspaces]=useState([]);
  const authHeaders=useCallback((json=true)=>{ const h={}; if(json) h["Content-Type"]="application/json"; if(authToken) h.Authorization=`Bearer ${authToken}`; return h; },[authToken]);
  const [voiceReplies,setVoiceReplies]=useState(()=>!!initPrefs.voiceReplies);
  const [settingsOpen,setSettingsOpen]=useState(false);
  const [settingsTab,setSettingsTab]=useState("general");
  const [terminalOpen,setTerminalOpen]=useState(()=>initPrefs.terminalOpen !== false);
  const [sideTab,setSideTab]=useState(()=>pick(initPrefs.sideTab,TABS.map(t=>t.id),"sessions"));
  const [rightPanel,setRightPanel]=useState(()=>pick(initPrefs.rightPanel,["trace","details","none"],"trace"));

  // -------------------- Workspace Manager State -------------------- #
  const [workspaces,setWorkspaces]=useState([]);
  const [activeWorkspace,setActiveWorkspace]=useState(null);

  const refreshWorkspaces=useCallback(async()=>{
    try{
      const r=await fetch("/api/workspace/list",{headers:authToken?{Authorization:`Bearer ${authToken}`}:{},cache:"no-store"});
      if(!r.ok) return;
      const d=await r.json();
      setWorkspaces(Array.isArray(d.workspaces)?d.workspaces:[]);
    }catch{}
  },[authToken]);

  const attachWorkspace=useCallback(async(path)=>{
    if(!path.trim()) return notify("Enter a directory path","warn");
    try{
      const id="ws_"+Date.now();
      const r=await fetch("/api/workspace/attach",{method:"POST",headers:authHeaders(),body:JSON.stringify({workspace_id:id,path})});
      if(!r.ok) throw new Error((await r.json().catch(()=>({}))).detail||"Attach failed");
      await refreshWorkspaces();
      setActiveWorkspace(id);
      notify(`Workspace attached: ${(await r.json()).file_count} files`,"ok");
    }catch(e){ notify(e.message||String(e),"error"); }
  },[authHeaders,notify,refreshWorkspaces]);

  const detachWorkspace=useCallback(async(id)=>{
    try{
      const r=await fetch("/api/workspace/detach",{method:"POST",headers:authHeaders(),body:JSON.stringify({workspace_id:id})});
      if(!r.ok) throw new Error("Detach failed");
      setWorkspaces(w=>w.filter(x=>x.workspace_id!==id));
      if(activeWorkspace===id) setActiveWorkspace(null);
      notify("Workspace detached","ok");
    }catch(e){ notify(e.message||String(e),"error"); }
  },[authHeaders,activeWorkspace,notify]);

  const browseWorkspaceDir=useCallback(async(wsId,dir=".")=>{
    try{
      const r=await fetch("/api/workspace/files/list",{method:"POST",headers:authHeaders(),body:JSON.stringify({workspace_id:wsId,directory:dir})});
      if(!r.ok) throw new Error("List failed");
      const d=await r.json();
      return d.items||[];
    }catch(e){ notify(e.message||String(e),"error"); return []; }
  },[authHeaders,notify]);

  const readWorkspaceFile=useCallback(async(wsId,filePath)=>{
    try{
      const r=await fetch("/api/workspace/files/read",{method:"POST",headers:authHeaders(),body:JSON.stringify({workspace_id:wsId,file_path:filePath})});
      if(!r.ok) throw new Error("Read failed");
      return (await r.json()).content||"";
    }catch(e){ notify(e.message||String(e),"error"); return ""; }
  },[authHeaders,notify]);

  const writeWorkspaceFile=useCallback(async(wsId,filePath,content)=>{
    try{
      const r=await fetch("/api/workspace/files/write",{method:"POST",headers:authHeaders(),body:JSON.stringify({workspace_id:wsId,file_path:filePath,content})});
      if(!r.ok) throw new Error("Write failed");
      notify("File written","ok");
    }catch(e){ notify(e.message||String(e),"error"); }
  },[authHeaders,notify]);

  const editWorkspaceFile=useCallback(async(wsId,filePath,oldStr,newStr)=>{
    try{
      const r=await fetch("/api/workspace/files/edit",{method:"POST",headers:authHeaders(),body:JSON.stringify({workspace_id:wsId,file_path:filePath,old_string:oldStr,new_string:newStr})});
      if(!r.ok) throw new Error("Edit failed");
      notify("File edited","ok");
    }catch(e){ notify(e.message||String(e),"error"); }
  },[authHeaders,notify]);

  const execWorkspaceCommand=useCallback(async(wsId,command,cwd=".")=>{
    try{
      const r=await fetch("/api/workspace/command/execute",{method:"POST",headers:authHeaders(),body:JSON.stringify({workspace_id:wsId,command,cwd})});
      if(!r.ok) throw new Error("Exec failed");
      return await r.json();
    }catch(e){ notify(e.message||String(e),"error"); return null; }
  },[authHeaders,notify]);
  const [density,setDensity]=useState(()=>pick(initPrefs.density,["comfortable","compact"],"comfortable"));
  const [copied,setCopied]=useState("");
  const [attachments,setAttachments]=useState([]);
  const [paletteOpen,setPaletteOpen]=useState(false);
  const [paletteSessions,setPaletteSessions]=useState([]);
  const [connection,setConnection]=useState({state:"checking",detail:""});
  const [lastSseAt,setLastSseAt]=useState(null);
  const [pendingRetry,setPendingRetry]=useState(null);
  const [latestCheckpoints,setLatestCheckpoints]=useState([]);
  const [openTabs,setOpenTabs]=useState([]);
  const [readProgress,setReadProgress]=useState(0);
  const [sidebarCollapsed,setSidebarCollapsed]=useState(()=>!!initPrefs.sidebarCollapsed);
  const [theme,setTheme]=useState(()=>{ const t=initPrefs.theme; if(t==="light"||t==="dark") return t; return window.matchMedia?.("(prefers-color-scheme: light)")?.matches ? "light" : "dark"; });
  const [lang,setLang]=useState(()=>initPrefs.lang==="en"?"en":"ar");
  const [advOpen,setAdvOpen]=useState(false);
  const [advView,setAdvView]=useState("models");
  const [ctxOpen,setCtxOpen]=useState(()=>initPrefs.contextOpen===true);
  const [ctxTab,setCtxTab]=useState("overview");
  const [mobileNav,setMobileNav]=useState(false);
  const chatEndRef=useRef(null), traceEndRef=useRef(null), termRef=useRef(null), inputRef=useRef(null), abortRef=useRef(null), fileRef=useRef(null), scrollRef=useRef(null);
  const reconnectRef=useRef({running:false,aborted:false,attempt:0});
  const sendLockRef=useRef(false);
  const errShownRef=useRef(false);
  const gotReplyRef=useRef(false);
  const lastPayloadRef=useRef(null);
  const connectedOnceRef=useRef(false);
  const wasDisconnectedRef=useRef(false);
  const pendingMetaRef=useRef({sources:[]});

  const { items: sessionCheckpoints, reload: reloadCheckpoints } = useCheckpoints(sessionId);

  useEffect(()=>{ setSessionId(crypto.randomUUID().replace(/-/g,"").slice(0,12)); },[]);

  // A different conversation must not inherit the previous task workspace.
  useEffect(()=>{ setExecTask(null); setExecArtifacts([]); },[sessionId]);

  useEffect(()=>{ setLatestCheckpoints(Array.isArray(sessionCheckpoints)?sessionCheckpoints.slice(0,12):[]); },[sessionCheckpoints]);

  useEffect(()=>{ if(messages.length===0 && !streamText) reloadCheckpoints(); },[messages.length,streamText,reloadCheckpoints]);

  const applyStatus = useCallback((s)=>{
    if(!s) return;
    setStatus(prev=>({state:s.state||prev.state||"sleeping",route:s.route||prev.route||"auto",providers:s.providers||prev.providers||{}}));
    setAuthRequired(!!s.auth_required);
    if(s.route && ROUTES.includes(s.route)) setRoute(r=>r==="auto"?s.route:r);
  },[]);

  const refreshStatus=useCallback(async(silent=false,source="manual")=>{
    try{
      setConnection(c=>c.state==="connected"?c:{state:"checking",detail:""});
      const r=await fetch("/api/status",{cache:"no-store"});
      if(!r.ok) throw new Error(`HTTP ${r.status}`);
      const s=await r.json();
      applyStatus(s);
      setConnection({state:"connected",detail:""});
      if(wasDisconnectedRef.current && (source==="reconnect" || source==="retry" || connectedOnceRef.current)) toast.success("Connection restored.");
      wasDisconnectedRef.current=false; connectedOnceRef.current=true;
      if(!silent) toast.success("Status updated.");
      return s;
    }
    catch(e){
      setConnection({state:"disconnected",detail:e?.message||"Network error"});
      wasDisconnectedRef.current=true;
      if(!silent) toast.error(`Failed to update status: ${e?.message||"Network error"}`);
      return null;
    }
  },[toast,applyStatus]);

  const refreshHistory = useCallback(async()=>{
    try{
      const r=await fetch("/api/history",{headers:authToken?{Authorization:`Bearer ${authToken}`}:{},cache:"no-store"});
      const d=await r.json().catch(()=>[]);
      setPaletteSessions(Array.isArray(d)?d:(d?.sessions||[]));
      return true;
    }
    catch{ return false; }
  },[authToken]);

  useEffect(()=>{ refreshStatus(true,"boot"); refreshHistory(); refreshWorkspaces(); },[refreshStatus,refreshHistory,refreshWorkspaces]);
  useEffect(()=>{ fetch("/api/workspace/list").then(r=>r.json()).then(d=>setProjectWorkspaces(Array.isArray(d?.workspaces)?d.workspaces:[])).catch(()=>{}); },[]);

  useEffect(()=>{ const onOnline=()=>refreshStatus(true,"online"); const onOffline=()=>{ setConnection({state:"disconnected",detail:"offline"}); wasDisconnectedRef.current=true; }; window.addEventListener("online",onOnline); window.addEventListener("offline",onOffline); return ()=>{ window.removeEventListener("online",onOnline); window.removeEventListener("offline",onOffline); }; },[refreshStatus]);

  useEffect(()=>{ if(!paletteOpen) return; refreshHistory(); },[paletteOpen,refreshHistory]);

  const [sessionLoading, setSessionLoading] = useState(false);
  const [sessionLoadError, setSessionLoadError] = useState("");
  useEffect(()=>{ let alive=true; (async()=>{ try{ const r=await fetch("/api/version",{cache:"no-store"}); if(!r.ok) return; const j=await r.json(); if(alive){ const el=document.getElementById("build-stamp-val"); if(el) el.textContent = j.build || j.asset || "unknown"; } }catch{} })(); return ()=>{ alive=false; }; },[]);

  useEffect(()=>{
    if(!sessionId) return;
    setOpenTabs(tabs=>{
      const idx = tabs.findIndex(t=>t.id===sessionId);
      const title = (messages.find(m=>m.role==="user")?.content || tabs[idx]?.title || (tabs.length?"Session":"New session")).slice(0,36);
      if(idx>=0){ const next=[...tabs]; next[idx]={...next[idx], title: next[idx].title||title}; return next; }
      return [...tabs.slice(-7), {id:sessionId, title}];
    });
  },[sessionId]); // eslint-disable-line

  const toastCopy=async(text,label="text")=>{ try{ await navigator.clipboard.writeText(text||""); setCopied(label); setTimeout(()=>setCopied(""),1200); toast.success("تم نسخ النص."); }catch{ toast.error("تعذر النسخ إلى الحافظة."); } };

  const loadSession=async(sid)=>{
    if(running) { toast.info("Stop the current run before switching sessions."); return; }
    setSessionLoadError("");
    if(!sid || sid==="new"){ const nid=(globalThis.crypto?.randomUUID?.()||`${Date.now()}${Math.random()}`).replace(/-/g,"").slice(0,12); setSessionId(nid); setMessages([]); setTrace([]); setToolLogs([]); setPlanSteps([]); setStreamText(""); setPendingRetry(null); setSessionLoading(false); toast.info("Started new session."); return; }
    const target = String(sid);
    setSessionLoading(true);
    try{
      const r=await fetch(`/api/history/${encodeURIComponent(target)}/detail?limit=500`,{headers:authToken?{Authorization:`Bearer ${authToken}`}:{} , cache:"no-store"});
      let hist = null;
      if(r.ok){ hist = await r.json().catch(()=>null); }
      if(!hist){
        const r2=await fetch(`/api/history/${encodeURIComponent(target)}`,{headers:authToken?{Authorization:`Bearer ${authToken}`}:{} , cache:"no-store"});
        if(!r2.ok){ let detail = `HTTP ${r2.status}`; try{ const j=await r2.json(); detail = j?.detail || j?.error || detail; }catch{} throw new Error(detail); }
        hist = await r2.json();
      }
      const arr = Array.isArray(hist) ? hist : Array.isArray(hist?.messages) ? hist.messages : Array.isArray(hist?.history) ? hist.history : Array.isArray(hist?.items) ? hist.items : [];
      const norm = (Array.isArray(arr)?arr:[]).map((m,i)=>{
        const role = (m && (m.role==="assistant" || m.role==="system" || m.role==="tool")) ? m.role : "user";
        const raw = m?.content ?? m?.text ?? m?.message ?? "";
        const content = typeof raw === "string" ? raw : (raw==null ? "" : JSON.stringify(raw,null,2));
        const safe = (m && typeof m==="object") ? m : {};
        return { ...safe, role: role==="tool"||role==="system" ? "assistant" : role, content, _k: safe.id||safe.ts||safe.created_at||i };
      });
      setSessionId(target); setMessages(norm); setTrace([]); setToolLogs([]); setPlanSteps([]); setStreamText(""); setPendingRetry(null); setSessionLoadError("");
    }
    catch(e){ const msg = e?.message || "خطأ في تحميل الجلسة"; setSessionLoadError(msg); setMessages([]); toast.error(`تعذر فتح الجلسة: ${msg}`); }
    finally { setSessionLoading(false); }
  };

  const speak=(text)=>{ try{ new Audio(`/api/tts?text=${encodeURIComponent(String(text).slice(0,800))}`).play().catch(()=>{});}catch{} };

  const renameSession = useCallback(async(sid,title)=>{
    const id = sid?.session_id || sid?.id || sid;
    if(!id) return;
    try{
      const r=await fetch(`/api/sessions/${encodeURIComponent(id)}`,{method:"PATCH",headers:authHeaders(),body:JSON.stringify({title})});
      if(!r.ok) throw new Error(`HTTP ${r.status}`);
      toast.success("Conversation renamed.");
      refreshHistory();
      setOpenTabs(ts=>ts.map(t=>t.id===id?{...t,title}:t));
    }catch(e){ toast.error(`Rename failed: ${e?.message||e}`); }
  },[authHeaders,toast,refreshHistory]);

  const pinSession = useCallback(async(sid,pinned)=>{
    const id = sid?.session_id || sid?.id || sid;
    if(!id) return;
    try{
      const r=await fetch(`/api/sessions/${encodeURIComponent(id)}`,{method:"PATCH",headers:authHeaders(),body:JSON.stringify({pinned:!!pinned})});
      if(!r.ok) throw new Error(`HTTP ${r.status}`);
      toast.success(pinned?"Pinned.":"Unpinned.");
      refreshHistory();
    }catch(e){ toast.error(`Pin failed: ${e?.message||e}`); }
  },[authHeaders,toast,refreshHistory]);

  const duplicateSession = useCallback(async(sid)=>{
    const id = sid?.session_id || sid?.id || sid;
    if(!id) return;
    try{
      const r=await fetch(`/api/sessions/${encodeURIComponent(id)}/duplicate`,{method:"POST",headers:authHeaders()});
      const d=await r.json().catch(()=>({}));
      if(!r.ok) throw new Error(d?.detail||`HTTP ${r.status}`);
      const nid = d?.session?.id || d?.id;
      toast.success("Conversation duplicated.");
      await refreshHistory();
      if(nid) loadSession(nid);
    }catch(e){ toast.error(`Duplicate failed: ${e?.message||e}`); }
  },[authHeaders,toast,refreshHistory]); // eslint-disable-line

  const deleteSession = useCallback(async(sid)=>{
    const id = sid?.session_id || sid?.id || sid;
    if(!id) return;
    if(!window.confirm("Delete this conversation? This cannot be undone.")) return;
    try{
      const r=await fetch(`/api/sessions/${encodeURIComponent(id)}`,{method:"DELETE",headers:authHeaders()});
      if(!r.ok) throw new Error(`HTTP ${r.status}`);
      toast.success("Conversation deleted.");
      setOpenTabs(ts=>ts.filter(t=>t.id!==id));
      if(id===sessionId) loadSession("new");
      await refreshHistory();
    }catch(e){ toast.error(`Delete failed: ${e?.message||e}`); }
  },[authHeaders,toast,refreshHistory,sessionId]); // eslint-disable-line

  const exportSession = useCallback(async(sid)=>{
    const id = sid || sessionId;
    if(!id) return;
    try{
      const r=await fetch(`/api/history/${encodeURIComponent(id)}/export?limit=5000`);
      const d=await r.json();
      const blob=new Blob([JSON.stringify(d,null,2)],{type:"application/json"});
      const a=document.createElement("a"); a.href=URL.createObjectURL(blob); a.download=`port777-${id}.json`;
      document.body.appendChild(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(a.href),1000);
      toast.success("Export downloaded.");
    }catch(e){ toast.error(`Export failed: ${e?.message||e}`); }
  },[sessionId,toast]);
  const login=async()=>{ const pw=window.prompt("Admin password (for protected actions when enabled):"); if(!pw) return; try{ const r=await fetch("/api/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({password:pw})}); if(r.ok){ const d=await r.json(); if(d.token){ localStorage.setItem("🔥😈 PORT 777 EVIL ☠️🔥👹_token",d.token); setAuthToken(d.token); toast.success("Logged in."); } else toast.error("No token received from server."); } else { toast.error(r.status===401?"Incorrect password.":`Login failed (HTTP ${r.status}).`); } }catch(e){ toast.error(`Login failed: ${e?.message||"network error"}`); } };

  useEffect(()=>{ chatEndRef.current?.scrollIntoView({behavior:"smooth"}); },[messages,streamText]);
  useEffect(()=>{ traceEndRef.current?.scrollIntoView({behavior:"smooth"}); },[trace]);
  useEffect(()=>{ if(termRef.current) termRef.current.scrollTop=termRef.current.scrollHeight; },[toolLogs]);
  useEffect(()=>{ try{ localStorage.setItem(PREFS_KEY, JSON.stringify({ route, model: chatModel, mode: composerMode, execEnv, sideTab, terminalOpen, rightPanel, voiceReplies, density, sidebarCollapsed, theme, lang, contextOpen: ctxOpen })); }catch{} },[route,chatModel,composerMode,execEnv,sideTab,terminalOpen,rightPanel,voiceReplies,density,sidebarCollapsed,theme,lang,ctxOpen]);

  // Load the verified runtime fingerprint + available environments once.
  const loadRuntime=useCallback(async()=>{
    try{
      const r=await fetch("/api/runtime",{cache:"no-store"});
      if(!r.ok) return;
      const d=await r.json();
      setRuntimeInfo(d.summary||null);
      setExecEnvs(Array.isArray(d.environments)?d.environments:[]);
    }catch{ /* backend may be down */ }
  },[]);
  useEffect(()=>{ loadRuntime(); },[loadRuntime]);

  useEffect(()=>{
    const root = document.documentElement;
    root.dataset.theme = theme;
    root.dataset.lang = lang;
    root.lang = lang;
    root.dir = lang === "ar" ? "rtl" : "ltr";
  document.title = "🔥😈 PORT 777 EVIL ☠️🔥👹";
  },[theme,lang]);

  const toggleTheme = useCallback(()=>setTheme(t=>t==="dark"?"light":"dark"),[]);
  const openAdvanced = useCallback((view="models", sid)=>{
    if(view==="export" && sid) setSessionId(sid);
    setAdvView(view); setAdvOpen(true); setMobileNav(false);
  },[]);

  const loadPersistedTimeline = useCallback(async (runId = "") => {
    if (!sessionId) { notify("No session selected", "warn"); return; }
    try {
      const qs = `limit=2000${runId ? `&run_id=${encodeURIComponent(runId)}` : ""}`;
      const r = await fetch(`/api/timeline/${encodeURIComponent(sessionId)}?${qs}`, { headers: authToken ? { Authorization: `Bearer ${authToken}` } : {}, cache: "no-store" });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(j?.detail || j?.error || `HTTP ${r.status}`);
      const items = Array.isArray(j?.trace_events) ? j.trace_events : [];
      const mapped = items.map((ev, i) => {
        const kind = ev?.kind || ev?.type || "thought";
        const data = ev?.data;
        let text = "";
        let tool = ev?.tool || "";
        if (typeof data === "string") {
          text = data;
        } else if (data && typeof data === "object") {
          tool = tool || data.tool || (data.data && data.data.tool) || "";
          if (typeof data.data === "string") text = data.data;
          else if (typeof data.text === "string") text = data.text;
          else if (typeof data.output === "string") text = data.output;
          else if (data.data && typeof data.data === "object" && typeof data.data.output === "string") text = data.data.output;
          else text = JSON.stringify(data.data ?? data, null, 2);
        } else {
          text = String(data ?? "");
        }
        return { kind, text, ts: ev?.ts, seq: ev?.seq ?? (i + 1), run_id: ev?.run_id || runId || "", tool, data };
      }).filter(ev => ev.kind !== "stream");
      if (mapped.length) {
        setTrace(mapped);
        notify(`Loaded ${mapped.length} trace event(s)${runId ? ` for run ${String(runId).slice(0,8)}` : ""}`, "ok");
      } else {
        setTrace([]);
        notify(runId ? `No trace events for run ${String(runId).slice(0,8)}` : "No persisted trace events for this session yet", "info");
      }
      // Only replace messages when loading full session timeline and chat is empty
      if (!runId && Array.isArray(j?.messages) && j.messages.length) {
        const norm = j.messages.map((m,i)=>({ role: (m.role==="assistant"||m.role==="system"||m.role==="tool")?"assistant":"user", content: String(m.content||""), _k: m.id||m.ts||i }));
        setMessages(prev => prev.length ? prev : norm);
      }
      return j;
    } catch (e) {
      notify(`Timeline load failed: ${e?.message || e}`, "error");
      throw e;
    }
  }, [sessionId, authToken, notify]);

  const pushTrace = useCallback((kind, payload = {}) => {
    const base = (payload && typeof payload === "object" && !Array.isArray(payload)) ? payload : { text: payload };
    const text = base.text ?? base.data ?? base.args ?? base.output ?? (typeof payload === "string" ? payload : "");
    const ev = { kind, ts: base.ts ?? Date.now()/1000, seq: base.seq, run_id: base.run_id || base.runId, tool: base.tool, ...base, text: typeof text === "string" ? text : (()=>{try{return JSON.stringify(text,null,2)}catch{return String(text)}})() };
    setTrace(t => [...t.slice(-1200), ev]);
  }, []);

  const handleEvent = useCallback((ev) => {
    setLastSseAt(Date.now());
    setConnection(c=>c.state==="connected"?c:{state:"connected",detail:""});
    wasDisconnectedRef.current=false; connectedOnceRef.current=true;
    const d = ev?.data;
    const meta = { ts: ev?.ts, seq: ev?.seq, run_id: ev?.run_id || ev?.runId };
    switch(ev?.type){
      case "run_start": pushTrace("run_start", { ...meta, text: `run ${d?.run_id || ev?.run_id || ""} started`, data: d }); break;
      case "reasoning": setReasoningLevel(d?.level??null); pushTrace("reasoning", { ...meta, text: `reasoning level ${d?.level} — ${d?.reason||""}`, data: d }); break;
      case "critique": setConfidenceScore(d?.passed ? (d?.action_count>0 ? 85 : 60) : 30); setCritiqueNotes(d?.notes||""); pushTrace("critique", { ...meta, text: `critique ${d?.passed?"passed":"failed"} — ${d?.notes||""}`, data: d }); break;
      case "exec": {
        if (d && d.ok === false) {
          notify(d.error || t("تعذّر بدء بيئة التنفيذ", "Could not start execution environment"), "error");
        } else if (d?.task) {
          setExecTask(d.task);
          setExecArtifacts([]);
          notify(`${t("بيئة التنفيذ", "Execution")}: ${d.task.env_label || d.task.env}`, "ok");
        }
        pushTrace("exec", { ...meta, text: d?.ok === false ? String(d.error||"") : `env ${d?.task?.env_label||""} task ${d?.task?.id||""}`, data: d });
        break;
      }
      case "artifacts": {
        const arts = Array.isArray(d?.artifacts) ? d.artifacts : (d?.artifact ? [d.artifact] : []);
        if (arts.length) setExecArtifacts(a => [...a, ...arts]);
        if (d?.task_id) setExecTask(t => (t && t.id === d.task_id) ? t : t);
        pushTrace("artifacts", { ...meta, text: arts.map(a=>a?.name||a?.url).filter(Boolean).join(", "), data: d });
        break;
      }
      case "vision": {
        pendingMetaRef.current.vision = d;
        pushTrace("vision", { ...meta, text: (d?.ok ? `vision ${d?.provider||""}/${d?.model||""}` : `vision failed: ${d?.error||""}`), data: d });
        if (d && d.ok === false) notify(d.error || t("تعذّر تحليل الصورة", "Vision analysis failed"), "error");
        break;
      }
      case "sources": {
        const items = Array.isArray(d?.items) ? d.items : [];
        const cur = Array.isArray(pendingMetaRef.current.sources) ? pendingMetaRef.current.sources : [];
        const seen = new Set(cur.map(s => s?.url));
        const fresh = items.filter(s => s?.url && !seen.has(s.url));
        pendingMetaRef.current.sources = [...cur, ...fresh].slice(-30);
        // Attached at "final": sources arrive before this run's assistant
        // message exists, and we must never mutate a previous reply.
        pushTrace("sources", { ...meta, text: fresh.map(s => s.title || s.url).join(", "), data: d });
        break;
      }
      case "status": applyStatus(typeof d==="object"?d:{state:d}); pushTrace("status", { ...meta, text: typeof d==="string"?d:JSON.stringify(d||{}) }); break;
      case "memory": pushTrace("memory", { ...meta, text: typeof d==="string"?d:JSON.stringify(d||{}) }); break;
      case "stream": { const chunk = typeof d==="string"?d:(d?.text||""); if(chunk) gotReplyRef.current=true; setStreamText(s=>s+chunk); break; }
      case "checkpoint": {
        const cp = (d && typeof d === "object") ? d : (d ? {id:String(d)} : null);
        if (cp) { setMessages(m=>{ const next=[...m]; for(let i=next.length-1;i>=0;i--){ if(next[i].role==="assistant"){ const ex=Array.isArray(next[i].checkpoints)?next[i].checkpoints:[]; next[i]={...next[i], checkpoints:[...ex,cp]}; return next; } } return [...next,{role:"assistant",content:"",checkpoints:[cp]}]; }); window.dispatchEvent(new Event("xxxgpt:checkpoints-refresh")); }
        break;
      }
      case "crew": setToolLogs(l=>[...l,`[crew] step ${d?.step} -> ${d?.agent}`]); pushTrace("crew", { ...meta, text: `step ${d?.step} -> ${d?.agent}`, data: d }); break;
      case "review": setToolLogs(l=>[...l,`[review] ${d?.verdict} ${d?.feedback||""}`]); pushTrace("review", { ...meta, text: `${String(d?.verdict||"").toUpperCase()} - ${d?.feedback||"ok"}`, data: d }); break;
      case "plan": setPlanSteps((d||[]).map(s=>({...s,state:"pending"}))); pushTrace("plan", { ...meta, text: (Array.isArray(d)?d:[]).map(s=>`${s.id}. ${s.title}`).join("\n"), data: d }); break;
      case "plan_step": setPlanSteps(ps=>ps.map(s=>String(s.id)===String(d?.id)?{...s,state:d?.state}:s)); if(d?.state==="running") setToolLogs(l=>[...l,`[plan] step ${d.id} -> ${d.title}`]); if(d?.state==="done"||d?.state==="failed") setToolLogs(l=>[...l,`[plan] step ${d.id} ${d.state}`]); pushTrace("plan_step", { ...meta, text: `step ${d?.id||""} ${d?.state||""} ${d?.title||""}`.trim(), data: d }); break;
      case "reflection": setToolLogs(l=>[...l,`[reflection] ${typeof d==="string"?d:JSON.stringify(d)}`]); pushTrace("reflection", { ...meta, text: typeof d==="string"?d:JSON.stringify(d||{}) }); break;
      case "thought": pushTrace("thought", { ...meta, text: typeof d==="string"?d:JSON.stringify(d||{}) }); break;
      case "action": setToolLogs(l=>[...l,`[action] ${d?.tool} ${JSON.stringify(d?.args||{})}`]); pushTrace("action", { ...meta, tool: d?.tool, text: typeof d?.args==="string"?d.args:JSON.stringify(d?.args||d||{},null,2), args: d?.args, data: d }); break;
      case "observation": setToolLogs(l=>[...l,`[output] ${typeof d?.output==="string"?d.output:JSON.stringify(d?.output||d)}`]); pushTrace("observation", { ...meta, tool: d?.tool, text: typeof d?.output==="string"?d.output:(typeof d==="string"?d:JSON.stringify(d?.output||d||{},null,2)), data: d }); break;
      case "final": gotReplyRef.current=true; setMessages(m=>{ const meta={ sources: pendingMetaRef.current.sources||[], ...(pendingMetaRef.current.vision?{vision:pendingMetaRef.current.vision}:{}) }; const next=[...m]; for(let i=next.length-1;i>=0;i--){ if(next[i].role==="assistant" && !next[i].content){ next[i]={...next[i], content:d, ...meta}; return next; } } return [...next,{role:"assistant",content:d,...meta}]; }); setStreamText(""); pushTrace("final", { ...meta, text: typeof d==="string"?d:JSON.stringify(d||{}) }); if(voiceReplies) speak(typeof d==="string"?d:""); window.dispatchEvent(new Event("xxxgpt:history-refresh")); window.dispatchEvent(new Event("xxxgpt:checkpoints-refresh")); break;
      case "error": {
        const msg = typeof d==="string"?d:(()=>{ try{ return JSON.stringify(d||{}); }catch{ return String(d); } })();
        setToolLogs(l=>[...l,`[error] ${msg}`]);
        pushTrace("error", { ...meta, text: msg });
        if(!errShownRef.current){
          errShownRef.current = true;
          setMessages(m=>[...m,{role:"assistant",content:`**Request failed**\n\n${msg}\n\nTry again in a moment, or pick another model from the selector.`,failed:true}]);
        }
        break;
      }
      case "done": pushTrace("done", { ...meta, text: typeof d==="string"?d:JSON.stringify(d||{}) }); break;
      default:
        if (ev?.type) pushTrace(ev.type, { ...meta, text: typeof d==="string"?d:JSON.stringify(d||ev||{}) });
        break;
    }
  }, [applyStatus, pushTrace, voiceReplies, notify]);

  const uploadAttachment=async(file)=>{ const fd=new FormData(); fd.append("file",file); try{ const r=await fetch("/api/files/upload",{method:"POST",headers:authToken?{Authorization:`Bearer ${authToken}`}:{},body:fd}); const j=await r.json().catch(()=>({})); if(r.ok){ setAttachments(a=>[...a,{name:file.name,ok:true,info:j}]); toast.success(`ØªÙ… Ø±ÙØ¹ Ø§Ù„Ù…Ø±ÙÙ‚: ${file.name}`); window.dispatchEvent(new Event("files-changed")); } else { const msg=j?.detail||j?.error||`HTTP ${r.status}`; setAttachments(a=>[...a,{name:file.name,ok:false,error:msg}]); toast.error(`ÙØ´Ù„ Ø±ÙØ¹ Ø§Ù„Ù…Ø±ÙÙ‚: ${msg}`); } }catch(e){ const msg=e?.message||"Ù…Ø´ÙƒÙ„Ø© Ø´Ø¨ÙƒØ©"; setAttachments(a=>[...a,{name:file.name,ok:false,error:msg}]); toast.error(`ÙØ´Ù„ Ø±ÙØ¹ Ø§Ù„Ù…Ø±ÙÙ‚: ${msg}`); } };

  const applySlashCommand = useCallback((raw)=>{
    const t = String(raw||"").trim();
    if(!t.startsWith("/")) return {handled:false,text:t};
    const [cmd,...rest] = t.slice(1).split(/\s+/);
    const arg = rest.join(" ").trim();
    const c = (cmd||"").toLowerCase();
    if(c==="mode" && arg){ const m = MODE_IDS.includes(arg)?arg:null; if(m){ setComposerMode(m); return {handled:true,note:`Mode: ${m}`}; } }
    if(c==="clear"){ setMessages([]); setTrace([]); setToolLogs([]); setPlanSteps([]); setStreamText(""); return {handled:true,note:"Cleared current view."}; }
    if(c==="save"){ toast.info("Session auto-persists in history."); return {handled:true}; }
    if(c==="help"){ return {handled:true,note:"Slash: /mode <code|plan|ask|debug>, /analyze <target>, /hunt <hypothesis>, /ioc <data>, /yara <desc>, /sigma <behavior>, /hash|/ip|/domain <value>, /clear"}; }
    const map = {
      analyze: `Analyze the following target/artifact in depth and produce findings, IOCs, MITRE TTPs, and next steps:\n${arg||"(provide target)"}`,
      hunt: `Start a threat hunt. Hypothesis/scope:\n${arg||"(provide hypothesis)"}\nProvide hunt queries, assumptions, data sources, and findings format.`,
      report: `Generate a structured report for this session/case:\n${arg||"Summarize current context, findings, IOCs, MITRE, and next steps."}`,
      yara: `Generate a valid YARA rule for:\n${arg||"(describe strings/behavior/sample)"}\nReturn rule, explanation, and validation notes.`,
      sigma: `Generate a Sigma rule for:\n${arg||"(describe behavior/artifact)"}\nReturn YAML and conversions (SPL/KQL/EQL) when possible.`,
      ioc: `Extract and normalize IOCs (IP/domain/url/hash/cve/email/path, defanged supported) from:\n${arg||"(paste data)"}`,
      mitre: `Map observed behaviors/this case to MITRE ATT&CK techniques with evidence and confidence:\n${arg||"(provide behavior/context)"}`,
      hash: `Analyze/enrich hash:\n${arg}\nReturn hash type, likely context, and lookup guidance.`,
      ip: `Enrich IP address:\n${arg}\nReturn reputation/context, related indicators, and investigation steps.`,
      domain: `Enrich domain:\n${arg}\nReturn reputation/context, related indicators, and investigation steps.`,
      sandbox: `Prepare a sandbox analysis plan and safe execution steps for:\n${arg||"windows|linux target"}`
    };
    if(map[c]) return {handled:false,text:map[c]};
    return {handled:false,text:t};
  },[toast]);

  const sendTask=async(override)=>{
    let payload = override || { text: input.trim(), attachments: [...attachments] };
    const rawText = String(payload.text||"").trim();
    if(!rawText||running||sendLockRef.current) return;
    if(!override){
      const sc = applySlashCommand(rawText);
      if(sc.handled){ if(sc.note) toast.info(sc.note); setInput(""); return; }
      payload = { ...payload, text: sc.text || rawText };
    }
    const text = String(payload.text||"").trim();
    if(!text) return;
    sendLockRef.current=true;
    errShownRef.current=false;
    gotReplyRef.current=false;
    pendingMetaRef.current={sources:[]};
    lastPayloadRef.current = payload;
    setPendingRetry(null);
    const finalText = (payload.attachments||[]).length ? `${text}\n\n[attachments]\n${(payload.attachments||[]).map(a=>`- ${a.name}: ${a.ok?"uploaded":"failed"}`).join("\n")}` : text;
    if(!override){ setInput(""); setAttachments([]); }
    setMessages(m=>[...m,{role:"user",content:finalText}]); setTrace([]); setToolLogs([]); setPlanSteps([]); setStreamText(""); setRunning(true);
    const ctrl=new AbortController(); abortRef.current=ctrl;
    let gotAny=false;
    let interrupted=false;
    try{
    const cluster = (v) => (["cloud", "upload", "sandbox"].includes(String(v || "")) ? "cloud" : String(v || ""));
    const reuseTask = (execEnv && execEnv !== "off" && execTask && execTask.status !== "cancelled"
      && (execTask.env === execEnv || execTask.requested_env === execEnv
          || cluster(execTask.env) === cluster(execEnv)))
      ? execTask.id : undefined;
    const execPayload = (execEnv && execEnv !== "off")
      ? { exec_env: execEnv, ...(reuseTask ? { exec_task_id: reuseTask } : {}), exec_approved: false }
      : {};
      const res=await fetch("/api/chat",{method:"POST",headers:authHeaders(),signal:ctrl.signal,body:JSON.stringify({message:finalText,session_id:sessionId,model:chatModel,model_route:route,mode:composerMode,full_access:fullAccess,project_path:projectPath,attachments:(payload.attachments||[]),...execPayload})});
      if(res.status===401){ toast.error("Ø§Ù„Ù…ØµØ§Ø¯Ù‚Ø© Ù…Ø·Ù„ÙˆØ¨Ø© Ù„Ù„Ø¥Ø¬Ø±Ø§Ø¡Ø§Øª Ø§Ù„Ù…Ø­Ù…ÙŠØ© Ø£Ùˆ Full Access."); setMessages(m=>[...m,{role:"assistant",content:"Authentication required for protected/full-access actions. Ø§ÙØªØ­ Settings > General ÙˆØ³Ø¬Ù‘Ù„ Ø§Ù„Ø¯Ø®ÙˆÙ„."}]); return; }
      if(!res.ok){ const t=await res.text().catch(()=>res.statusText); throw new Error(`HTTP ${res.status}: ${t.slice(0,220)}`); }
      const reader=res.body.getReader(); const dec=new TextDecoder(); let buf="";
      while(true){ const {value,done}=await reader.read(); if(done) break; gotAny=true; buf+=dec.decode(value,{stream:true}); const parts=buf.split("\n\n"); buf=parts.pop()??""; for(const p of parts){ if(!p.startsWith("data:")) continue; try{ handleEvent(JSON.parse(p.replace(/^data:\s*/,""))); }catch{} } }
      setPendingRetry(null);
    }catch(err){
      if(err?.name!=="AbortError"){
        const msg=err?.message||"Ù…Ø´ÙƒÙ„Ø© Ø´Ø¨ÙƒØ©/Ø®Ø§Ø¯Ù…";
        interrupted=true;
        setConnection({state:"disconnected",detail:msg}); wasDisconnectedRef.current=true;
        setToolLogs(l=>[...l,`[fatal] ${String(err)}`]);
        setMessages(m=>[...m,{role:"assistant",content:`Ø§Ù†Ù‚Ø·Ø¹ Ø§Ù„Ø§ØªØµØ§Ù„ Ø£Ø«Ù†Ø§Ø¡ Ø§Ù„Ù…Ø¹Ø§Ù„Ø¬Ø©: ${msg}`,failed:true}]);
        setPendingRetry({payload, partial: !!(streamText || trace.length || toolLogs.length || gotAny), reason: msg});
        toast.error(`Ø§Ù†Ù‚Ø·Ø¹ Ø§Ù„Ø§ØªØµØ§Ù„: ${msg}`);
      }
    }
    finally{
      setRunning(false); sendLockRef.current=false; setStatus(s=>({...s,state:"sleeping"})); abortRef.current=null;
      if(!gotReplyRef.current && !errShownRef.current && !interrupted){
        setMessages(m=>[...m,{role:"assistant",content:"**No response received**\n\nThe request ended without a reply. This is usually a temporary provider issue (rate limit or cooldown).\n\nTry again, or choose another model from the selector.",failed:true}]);
      }
      if(interrupted) attemptReconnect();
      else { refreshHistory(); if(gotAny) try{ emitXp("analysis_complete"); }catch{} }
    }
  };

  const attemptReconnect = useCallback(async()=>{
    const st = reconnectRef.current;
    if(st.running) return;
    st.running=true; st.aborted=false; st.attempt=0;
    for(let i=0;i<BACKOFF.length;i++){
      if(st.aborted) break;
      st.attempt=i+1;
      setConnection({state:"reconnecting",detail:`Ù…Ø­Ø§ÙˆÙ„Ø© ${i+1}/${BACKOFF.length}`});
      await new Promise(res=>setTimeout(res,BACKOFF[i]));
      if(st.aborted) break;
      const ok = await refreshStatus(true,"reconnect");
      if(ok){ await refreshHistory(); st.running=false; return true; }
    }
    setConnection({state:"disconnected",detail:"ÙØ´Ù„ Ø¥Ø¹Ø§Ø¯Ø© Ø§Ù„Ø§ØªØµØ§Ù„ Ø¨Ø¹Ø¯ 5 Ù…Ø­Ø§ÙˆÙ„Ø§Øª"});
    toast.error("ØªØ¹Ø°Ø± Ø¥Ø¹Ø§Ø¯Ø© Ø§Ù„Ø§ØªØµØ§Ù„ ØªÙ„Ù‚Ø§Ø¦ÙŠØ§Ù‹. Ø§Ø³ØªØ®Ø¯Ù… Ø²Ø± Ø¥Ø¹Ø§Ø¯Ø© Ø§Ù„Ù…Ø­Ø§ÙˆÙ„Ø©.");
    st.running=false;
    return false;
  },[refreshStatus,refreshHistory,toast]);

  const retryConnection = useCallback(async()=>{
    reconnectRef.current.aborted=true; reconnectRef.current.running=false;
    const ok = await refreshStatus(true,"retry");
    if(ok){ await refreshHistory(); toast.success("Ø§Ù„Ø§ØªØµØ§Ù„ Ù†Ø´Ø·."); } else attemptReconnect();
  },[refreshStatus,refreshHistory,toast,attemptReconnect]);

  // Regenerate / retry the last payload. Declared before the shortcut effect
  // below so the effect's dependency array can reference it (avoids TDZ).
  const regenerate = useCallback(()=>{
    const p = lastPayloadRef.current;
    if(!p || running || sendLockRef.current) return;
    sendTask({ ...p, attachments: Array.isArray(p.attachments)?[...p.attachments]:[] });
  },[running]);


  useEffect(()=>{
    const onInsert=(e)=>{ const t=e?.detail?.text; if(typeof t==="string" && t) setInput(v=>v?`${v}\n${t}`:t); inputRef.current?.focus(); };
    window.addEventListener("xxxgpt:composer-insert", onInsert);
    return ()=>window.removeEventListener("xxxgpt:composer-insert", onInsert);
  },[]);
  useEffect(()=>{ window.addEventListener("xxxgpt:history-refresh", refreshHistory); return ()=>window.removeEventListener("xxxgpt:history-refresh", refreshHistory); },[refreshHistory]);

  useEffect(()=>{
    const onKey=(e)=>{
      if((e.ctrlKey||e.metaKey)&&e.key===","){ e.preventDefault(); setPaletteOpen(false); setSettingsOpen(true); }
      if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){ e.preventDefault(); if(settingsOpen) return; setPaletteOpen(v=>!v); }
      if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="l"){ e.preventDefault(); setPaletteOpen(false); inputRef.current?.focus(); }
      if((e.ctrlKey||e.metaKey)&&e.key==="/"){ e.preventDefault(); setSidebarCollapsed(v=>!v); }
      if((e.ctrlKey||e.metaKey)&&e.shiftKey&&e.key.toLowerCase()==="n"){ e.preventDefault(); loadSession("new"); }
      if((e.ctrlKey||e.metaKey)&&e.shiftKey&&e.key.toLowerCase()==="r"){ e.preventDefault(); regenerate(); }
      if(e.key==="Escape"){ if(paletteOpen){ e.preventDefault(); setPaletteOpen(false); } else if(settingsOpen) setSettingsOpen(false); else if(running) abortRef.current?.abort(); }
    };
    window.addEventListener("keydown", onKey); return ()=>window.removeEventListener("keydown", onKey);
  },[settingsOpen,running,paletteOpen,regenerate]); // eslint-disable-line


  const canSend = !!input.trim() && !running && connection.state !== "reconnecting";
  const hasPrevUser = messages.some(m=>m.role==="user") || !!lastPayloadRef.current;
  const clearComposer = ()=>{ if(running) return; setInput(""); };
  const removeAttachment = (idx)=>setAttachments(a=>a.filter((_,i)=>i!==idx));

  const enhancePrompt = useCallback(async()=>{
    const text = input.trim();
    if(!text || running || enhancing) return;
    setEnhancing(true);
    try {
      const res = await fetch("/api/prompt/enhance", { method:"POST", headers: authHeaders(), body: JSON.stringify({ text, mode: composerMode }) });
      const data = await res.json().catch(()=>({}));
      if(!res.ok) throw new Error(data?.detail || data?.error || `HTTP ${res.status}`);
      const improved = typeof data?.text === "string" ? data.text.trim() : "";
      if(improved) { setInput(improved); toast.success("ØªÙ… ØªØ­Ø³ÙŠÙ† Ø§Ù„Ø¨Ø±ÙˆÙ…Ø¨Øª — ÙŠÙ…ÙƒÙ†Ùƒ ØªØ¹Ø¯ÙŠÙ„Ù‡ Ù‚Ø¨Ù„ Ø§Ù„Ø¥Ø±Ø³Ø§Ù„."); inputRef.current?.focus(); }
      else toast.info("Ù„Ù… ÙŠØªØºÙŠØ± Ø§Ù„Ù†Øµ.");
    } catch(e){ toast.error(`ÙØ´Ù„ ØªØ­Ø³ÙŠÙ† Ø§Ù„Ø¨Ø±ÙˆÙ…Ø¨Øª: ${e?.message||"Ø®Ø·Ø£"}`); }
    finally { setEnhancing(false); }
  },[input,running,enhancing,authHeaders,composerMode,toast]);

  const sendFeedback = useCallback(async(message, idx, vote)=>{
    try {
      const payload = { session_id: sessionId || "", message_id: String(message?.id ?? message?._k ?? `idx:${idx}`), vote: vote>0 ? 1 : -1 };
      const res = await fetch("/api/feedback", { method:"POST", headers: authHeaders(), body: JSON.stringify(payload) });
      const data = await res.json().catch(()=>({}));
      if(!res.ok) throw new Error(data?.detail || data?.error || `HTTP ${res.status}`);
      toast.info(vote>0 ? "Ø´ÙƒØ±Ù‹Ø§ — ØªÙ… ØªØ³Ø¬ÙŠÙ„ ðŸ‘" : "ØªÙ… ØªØ³Ø¬ÙŠÙ„ ðŸ‘Ž");
    } catch(e){ toast.error(`ØªØ¹Ø°Ø± Ø¥Ø±Ø³Ø§Ù„ Ø§Ù„ØªÙ‚ÙŠÙŠÙ…: ${e?.message||"Ø®Ø·Ø£"}`); }
  },[sessionId,authHeaders,toast]);

  const paletteCommands = useMemo(()=>{
    const cmds = [
      {id:"new-session", label:"جلسة جديدة", hint:"Ctrl+Shift+N", icon:"plus", group:"جلسة", run:()=>loadSession("new")},
      {id:"focus-composer", label:"تركيز مربع الإرسال", hint:"Ctrl+L", icon:"chat", group:"تنقل", run:()=>inputRef.current?.focus()},
      {id:"toggle-sidebar", label:sidebarCollapsed?"إظهار Sidebar":"إخفاء Sidebar", hint:"Ctrl+/", icon:"folder", group:"عرض", run:()=>setSidebarCollapsed(v=>!v)},
      {id:"settings", label:"فتح الإعدادات", hint:"Ctrl+,", icon:"settings", group:"تنقل", run:()=>setSettingsOpen(true)},
      {id:"refresh-status", label:"تحديث الحالة", hint:"جلب /api/status", icon:"refresh", group:"نظام", run:()=>refreshStatus(false)},
      {id:"retry-conn", label:"إعادة محاولة الاتصال", hint:"فحص backend وجلب البيانات", icon:"activity", group:"نظام", run:()=>retryConnection()},
      {id:"toggle-trace", label:ctxOpen?"إخفاء لوحة التفاصيل":"إظهار لوحة التفاصيل", hint:"الخطة والنشاط والملفات", icon:"panelRight", group:"عرض", run:()=>setCtxOpen(v=>!v)},
      {id:"toggle-activity", label:"سجل النشاط المتقدم", hint:"Tool calls + traces", icon:"activity", group:"عرض", run:()=>openAdvanced("activity")},
      {id:"regenerate", label:"إعادة توليد آخر رد", hint:"Ctrl+Shift+R", icon:"refresh", group:"جلسة", run:()=>regenerate()},
      {id:"refresh-checkpoints", label:"تحديث Checkpoints", hint:"آخر نقاط استرجاع للجلسة", icon:"history", group:"Checkpoints", run:()=>{ reloadCheckpoints(); toast.info("تم تحديث checkpoints"); }},
    ];
    const slash = [["/analyze","Start malware/target analysis","تحليل"],["/hunt","Start threat hunt","صيد"],["/report","Generate report","تقرير"],["/yara","Generate YARA rule","أدوات"],["/sigma","Generate Sigma rule","أدوات"],["/ioc","Extract IOCs","أدوات"],["/mitre","Map to MITRE ATT&CK","أدوات"],["/hash","Lookup hash","إثراء"],["/ip","Lookup IP","إثراء"],["/domain","Lookup domain","إثراء"],["/mode code|plan|ask|debug","Switch response mode","وضع"],["/clear","Clear current view","جلسة"]];
    slash.forEach(([label,hint,group])=>cmds.push({id:`slash-${label}`, label, hint, icon:"terminal", group, run:()=>{ setInput(v=>v&&v.trim()?v:label+" "); setPaletteOpen(false); inputRef.current?.focus(); }}));
    TABS.forEach(t=>cmds.push({id:`panel-${t.id}`, label:`فتح ${t.label}`, hint:"أدوات متقدمة", icon:t.icon, group:"أدوات", run:()=>{
      if (t.id === "workspace") { setSideTab("workspace"); return; }
      const map={gateway:"models",sandbox:"sandbox",tools:"tools",ops:"ops",plugins:"plugins",progress:"progress"};
      openAdvanced(map[t.id]||t.id);
    }}));
    (paletteSessions||[]).slice(0,80).forEach(s=>{
      const id=s.session_id||s.id; if(!id) return;
      cmds.push({id:`session-${id}`, label:s.title||id, hint:`فتح جلسة · ${s.n??0} رسالة`, icon:"history", group:"جلسات", run:()=>loadSession(id)});
    });
    (latestCheckpoints||[]).slice(0,30).forEach((cp)=>{
      const n = Array.isArray(cp.files)?cp.files.length:0;
      const ts = cp.ts ? new Date(cp.ts*1000).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"}) : "—";
      cmds.push({
        id:`checkpoint-${cp.id}`,
        label:`Checkpoint ${ts} · ${n} files`,
        hint:cp.message_id || cp.id,
        icon:"search",
        group:"Checkpoints",
        run: async ()=>{
          try {
            await fetch(`/api/checkpoints/${encodeURIComponent(cp.id)}/diff?session_id=${encodeURIComponent(sessionId||"")}`).then(r=>r.json());
            setMessages(m=>[...m,{role:"assistant", content:`Checkpoint ${cp.id}\n${ts} · ${n} files`, checkpoints:[cp]}]);
            toast.info("تم فتح checkpoint في المحادثة (Diff/Revert).");
          } catch(e){ toast.error(`تعذر فتح checkpoint: ${e?.message||"خطأ"}`); }
        }
      });
    });
    return cmds;
  },[paletteSessions,ctxOpen,refreshStatus,retryConnection,latestCheckpoints,sessionId,reloadCheckpoints,toast,sidebarCollapsed,regenerate,openAdvanced]); // eslint-disable-line


  setUiLang(lang);

  return (
    <div className={`app2 ${sidebarCollapsed ? "sb-collapsed" : ""} ${ctxOpen ? "has-context" : ""} ${mobileNav ? "sb-open" : ""}`}>
      <Sidebar
        sessions={paletteSessions}
        activeId={sessionId}
        onSelect={(id) => { setMobileNav(false); loadSession(id); }}
        onNew={() => { setMobileNav(false); loadSession("new"); }}
        onRename={renameSession}
        onPin={pinSession}
        onDelete={deleteSession}
        onDuplicate={duplicateSession}
        onOpen={(v, sid) => {
          setMobileNav(false);
          if (v === "export") { exportSession(sid); return; }
          const map = { library: "memory", extensions: "mcp" };
          openAdvanced(map[v] || v, sid);
        }}
        onSettings={() => setSettingsOpen(true)}
        onToggleTheme={toggleTheme}
        theme={theme}
        lang={lang}
        onToggleLang={() => setLang(l => (l === "ar" ? "en" : "ar"))}
        onCollapse={() => setSidebarCollapsed(true)}
        disconnected={connection.state === "disconnected"}
      />

      <main className="main2">
        <header className="topbar2">
          <button type="button" className="icon-btn" title={t("القائمة", "Menu")} aria-label={t("القائمة", "Menu")} onClick={() => { setMobileNav(v => !v); if (sidebarCollapsed) setSidebarCollapsed(false); }}><Icon name="menu" size={17} /></button>
          {sidebarCollapsed && (
            <button type="button" className="icon-btn" title="Show sidebar (Ctrl+/)" onClick={() => setSidebarCollapsed(false)}><Icon name="sidebar" size={16} /></button>
          )}
          <div className="top-title2">
            <span className="t">{(paletteSessions.find(s => (s.session_id || s.id) === sessionId)?.title) || (messages.length ? t("محادثة", "Conversation") : t("محادثة جديدة", "New chat"))}</span>
            <span className="s">
              {running ? t("جارٍ العمل…", "Working…") : connection.state === "connected" ? (status.state === "sleeping" ? t("جاهز", "Ready") : String(status.state || "ready").replace(/_/g, " ")) : connection.state}
            </span>
          </div>
          <div className="top-spacer" />
          <div className="top-actions">
            <span className={`conn-dot ${connection.state === "connected" ? (running ? "run" : "ok") : "err"}`} title={connection.detail || connection.state} />
            <button type="button" className={`icon-btn ${fullAccess ? "on" : ""}`} title={fullAccess ? t("الوصول الكامل: مفعّل", "Full access: on") : t("الوصول الكامل: متوقف", "Full access: off")} aria-label="Full access" onClick={() => { if (!fullAccess && !window.confirm("Enable Full Access for this session? Backend permissions still apply.")) return; setFullAccess(v => !v); }}>
              <Icon name={fullAccess ? "shield" : "lock"} size={16} />
            </button>
            <button type="button" className="icon-btn" title={t("الإضافات والتكاملات", "Plugins & integrations")} aria-label="Plugins" onClick={() => openAdvanced("plugins")}>
              <Icon name="plug" size={16} />
            </button>
          </div>
        </header>

        <div className="chat-scroll">
          <div className="chat-inner">
            {messages.length === 0 && !streamText ? (
              <Welcome
                model={chatModel}
                onPick={(p) => { setInput(p); inputRef.current?.focus(); }}
              />
            ) : (
              <div className="msgs">
                {messages.map((m, i) => (
                  <Message
                    key={m?._k ?? i}
                    m={m}
                    index={i}
                    sessionId={sessionId}
                    toast={toast}
                    onCopy={(t) => toastCopy(t, "msg")}
                    onFeedback={sendFeedback}
                    onRegenerate={() => regenerate()}
                    onEdit={(txt) => { setInput(txt); inputRef.current?.focus(); }}
                    onRetry={() => regenerate()}
                    onOpenContext={() => { setCtxTab("overview"); setCtxOpen(true); }}
                    running={running}
                    onAfterRevert={() => loadSession(sessionId)}
                  />
                ))}

                {streamText && (
                  <div className="msg2 assistant">
                    <div className="msg-avatar"><Icon name="spark" size={14} /></div>
                    <div className="msg-main">
                      <div className="msg-head"><span className="who">🔥😈 PORT 777 EVIL ☠️🔥👹</span><span className="tag">AI</span><span style={{ color: "var(--accent)" }}>{String(status.state || "working").replace(/_/g, " ")}</span></div>
                      <div className="bubble2 streaming"><Markdown text={streamText} /><span className="cursor" /></div>
                      <div className="msg-actions"><button type="button" className="mini-btn" onClick={() => abortRef.current?.abort()}><Icon name="stop" size={12} />Stop</button></div>
                    </div>
                  </div>
                )}

                {running && !streamText && (
                  <div className="msg2 assistant">
                    <div className="msg-avatar"><Icon name="spark" size={14} /></div>
                    <div className="msg-main">
                      <div className="msg-head"><span className="who">🔥😈 PORT 777 EVIL ☠️🔥👹</span><span className="tag">AI</span></div>
                      <div className="bubble2"><span className="muted">{t("جارٍ التفكير…", "Thinking…")}</span> <span className="cursor" /></div>
                    </div>
                  </div>
                )}

                {execArtifacts.length > 0 && (
                  <div className="attach-strip" style={{ justifyContent: "flex-start", padding: "6px 2px" }}>
                    <span style={{ fontSize: 11.5, color: "var(--muted)" }}>{t("ملفات الناتج", "Artifacts")}:</span>
                    {execArtifacts.map((a, i) => (
                      <a
                        key={`${a.url || a.name}-${i}`}
                        className="attach-chip"
                        href={a.url || (execTask?.id ? `/api/exec/tasks/${execTask.id}/archive` : "#")}
                        target="_blank"
                        rel="noreferrer"
                        title={a.name}
                      >
                        <Icon name="download" size={12} />
                        <span className="nm">{a.name || t("تنزيل", "download")}</span>
                      </a>
                    ))}
                    {execTask?.id && (
                      <button type="button" className="mini-btn" onClick={() => openAdvanced("exec")}>
                        {t("كل الملفات", "All files")}
                      </button>
                    )}
                  </div>
                )}

                <div ref={chatEndRef} />
              </div>
            )}
          </div>
        </div>

        <div style={{ maxWidth: "var(--composer-max)", margin: "0 auto 6px", width: "100%", padding: "0 24px", display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          <Icon name="folder" size={13} />
          <span style={{ fontSize: 11, color: "var(--muted)" }}>{t("المشروع النشط", "Active project")}</span>
          <select className="input" style={{ maxWidth: 260 }} value={projectPath} onChange={(e) => { const v = e.target.value; setProjectPath(v); setProjectInput(v); if (v) localStorage.setItem("port777_project", v); else localStorage.removeItem("port777_project"); }}>
            <option value="">{t("بدون مشروع", "No project")}</option>
            {projectPath && !projectWorkspaces.some((w) => w.path === projectPath) && (
              <option value={projectPath}>{projectPath}</option>
            )}
            {projectWorkspaces.map((w) => <option key={w.workspace_id} value={w.path}>{w.workspace_id} · {w.path}</option>)}
          </select>
          <input className="input" style={{ flex: 1, minWidth: 160 }} placeholder="D:/path/to/project" value={projectInput} onChange={(e) => setProjectInput(e.target.value)} />
          <button type="button" className="btn sm ghost" onClick={() => { const v = projectInput.trim(); setProjectPath(v); setProjectInput(v); if (v) localStorage.setItem("port777_project", v); else localStorage.removeItem("port777_project"); }}>{t("اختيار", "Select")}</button>
          {projectPath && <button type="button" className="btn sm ghost" onClick={() => { setProjectPath(""); setProjectInput(""); localStorage.removeItem("port777_project"); }}>{t("إزالة", "Clear")}</button>}
        </div>

        {connection.state !== "connected" && (
          <div style={{ maxWidth: "var(--composer-max)", margin: "0 auto", width: "100%", padding: "0 24px" }}>
            <div className="banner">
              <Icon name="alert" size={15} />
              <span style={{ flex: 1 }}>{connection.state === "reconnecting" ? t("جارٍ إعادة الاتصال…", "Reconnecting to the workspace…") : t("الاتصال بالخادم مقطوع", "Backend disconnected")}{pendingRetry ? t(" · يمكن إعادة إرسال طلبك الأخير", " · your last request can be resent") : ""}</span>
              <button type="button" className="btn sm" onClick={retryConnection} disabled={connection.state === "reconnecting"}><Icon name="refresh" size={13} />{t("إعادة المحاولة", "Retry")}</button>
              {pendingRetry && !running && <button type="button" className="btn sm primary" onClick={() => sendTask(pendingRetry.payload)}><Icon name="send" size={13} />{t("إعادة الإرسال", "Resend")}</button>}
            </div>
          </div>
        )}

        <Composer
          value={input}
          onChange={setInput}
          onSend={() => sendTask()}
          running={running}
          onStop={() => abortRef.current?.abort()}
          model={chatModel}
          onModel={setChatModel}
          mode={composerMode}
          onMode={setComposerMode}
          execEnv={execEnv}
          onExecEnv={setExecEnv}
          execEnvs={execEnvs}
          execTask={execTask}
          onOpenExec={() => openAdvanced("exec")}
          attachments={attachments}
          onAttach={async (files) => { for (const f of files) await uploadAttachment(f); }}
          onRemoveAttachment={(i) => setAttachments(a => a.filter((_, n) => n !== i))}
          onToast={notify}
          fullAccess={fullAccess}
          onFullAccess={(v) => {
            if (v && !window.confirm("Enable Full Access for this task? Backend and tool permissions still apply.")) return;
            setFullAccess(v);
          }}
          voiceReplies={voiceReplies}
          onVoiceReplies={setVoiceReplies}
          onAdvanced={(v) => openAdvanced(v)}
          onClear={() => { setMessages([]); setTrace([]); setToolLogs([]); setPlanSteps([]); setStreamText(""); toast.info(t("تم مسح المحادثة.", "Conversation cleared.")); }}
          inputRef={inputRef}
          disabled={connection.state === "disconnected"}
        />
      </main>




      {advOpen && (
        <React.Suspense fallback={<div style={{padding:20}}>جاري التحميل…</div>}>
          <Advanced
            view={advView}
            setView={setAdvView}
            onClose={() => setAdvOpen(false)}
            sessionId={sessionId}
            notify={notify}
            chatModel={chatModel}
            setChatModel={setChatModel}
            trace={trace}
            toolLogs={toolLogs}
            planSteps={planSteps}
            status={status}
            authToken={authToken}
            onAfterRevert={() => loadSession(sessionId)}
            onUsePrompt={(text) => { setInput(text); setAdvOpen(false); inputRef.current?.focus(); }}
            execTaskId={execTask?.id}
            onExecTask={(t2) => { setExecTask(t2); loadRuntime(); }}
          />
        </React.Suspense>
      )}

      {settingsOpen && (
        <Settings
          open={settingsOpen}
          tab={settingsTab}
          setTab={setSettingsTab}
          onClose={() => setSettingsOpen(false)}
          route={route}
          setRoute={setRoute}
          routes={ROUTES}
          fullAccess={fullAccess}
          setFullAccess={setFullAccess}
          voiceReplies={voiceReplies}
          setVoiceReplies={setVoiceReplies}
          density={density}
          setDensity={setDensity}
          authRequired={authRequired}
          authToken={authToken}
          login={login}
          status={status}
          sessionId={sessionId}
        />
      )}

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} commands={paletteCommands} />
    </div>
  );
}
