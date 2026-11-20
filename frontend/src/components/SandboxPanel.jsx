// @ts-nocheck
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Icon from "./Icon.jsx";

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  const tok = localStorage.getItem("🔥😈 PORT 777 EVIL ☠️🔥👹_token");
  if (tok) headers.Authorization = `Bearer ${tok}`;
  const res = await fetch(path, { ...opts, headers });
  const ct = res.headers.get("content-type") || "";
  const data = ct.includes("application/json") ? await res.json().catch(()=>null) : await res.text().catch(()=>null);
  if (!res.ok) {
    const msg = (data && (data.detail || data.error || data.message)) || `HTTP ${res.status}`;
    const e = new Error(String(msg)); e.status = res.status; e.data = data; throw e;
  }
  return data;
}

const pill = (st) => {
  const s = String(st||"idle").toLowerCase();
  const color = s==="running"?"#22c55e":s==="starting"?"#f59e0b":s==="destroyed"?"#ef4444":"#94a3b8";
  return <span style={{padding:"2px 8px",border:"1px solid rgba(204,0,0,.35)",borderRadius:999,fontSize:11,color,background:"rgba(0,0,0,.35)",textTransform:"uppercase",letterSpacing:.4}}>{s}</span>;
};

export default function SandboxPanel({ notify }) {
  const [caps, setCaps] = useState(null);
  const [tab, setTab] = useState("linux"); // linux | windows
  const [distro, setDistro] = useState("ubuntu:22.04");
  const [session, setSession] = useState(null);
  const [busy, setBusy] = useState(false);
  const [cmd, setCmd] = useState("uname -a || ver");
  const [shell, setShell] = useState("powershell");
  const [results, setResults] = useState(null);
  const [note, setNote] = useState("");
  const [uploading, setUploading] = useState(false);
  const pollRef = useRef(null);
  const say = (m,k="info") => notify ? notify(m,k) : null;

  const refreshCaps = useCallback(async()=>{
    try { setCaps(await api("/api/sandbox/capabilities")); } catch(e){ say(e.message||String(e),"error"); }
  },[]);

  useEffect(()=>{ refreshCaps(); return ()=>{ if(pollRef.current) clearInterval(pollRef.current); }; },[refreshCaps]);

  const sid = session?.id;
  const refreshStatus = useCallback(async()=>{
    if(!sid) return;
    try {
      const st = await api(`/api/sandbox/${encodeURIComponent(sid)}/status`);
      setSession(prev => ({...(prev||{}), ...st}));
    } catch(e){ /* ignore transient */ }
  },[sid]);

  const refreshResults = useCallback(async()=>{
    if(!sid) return;
    try { setResults(await api(`/api/sandbox/${encodeURIComponent(sid)}/results`)); } catch(e){ /* ignore */ }
  },[sid]);

  useEffect(()=>{
    if(pollRef.current) clearInterval(pollRef.current);
    if(sid){
      pollRef.current = setInterval(()=>{ refreshStatus(); refreshResults(); }, 4000);
      refreshStatus(); refreshResults();
    }
    return ()=>{ if(pollRef.current) clearInterval(pollRef.current); };
  },[sid, refreshStatus, refreshResults]);

  const start = async()=>{
    setBusy(true);
    try {
      const out = await api(`/api/sandbox/${tab}/start`, {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({distro: tab==="linux"?distro:""})});
      setSession(out); setResults(null);
      say(`Sandbox ${tab} session started (${out.backend||"local"})`, "ok");
    } catch(e){ say(e.message||String(e),"error"); }
    finally{ setBusy(false); }
  };

  const destroy = async()=>{
    if(!sid) return;
    setBusy(true);
    try {
      await api(`/api/sandbox/${encodeURIComponent(sid)}/destroy`, {method:"POST"});
      setSession(prev => prev ? ({...prev,status:"destroyed"}) : prev);
      say("Sandbox session destroyed", "ok");
    } catch(e){ say(e.message||String(e),"error"); }
    finally{ setBusy(false); }
  };

  const run = async()=>{
    if(!sid || !cmd.trim()) return;
    setBusy(true);
    try {
      const out = await api(`/api/sandbox/${encodeURIComponent(sid)}/execute`, {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({command: cmd, timeout: 90, shell: tab==="windows"?shell:"sh"})});
      await refreshResults(); await refreshStatus();
      say(out?.ok ? "Command completed" : "Command finished with errors", out?.ok?"ok":"warn");
    } catch(e){ say(e.message||String(e),"error"); }
    finally{ setBusy(false); }
  };

  const snapshot = async()=>{
    if(!sid) return;
    setBusy(true);
    try {
      await api(`/api/sandbox/${encodeURIComponent(sid)}/snapshot`, {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({note})});
      await refreshResults();
      say("Snapshot captured", "ok");
    } catch(e){ say(e.message||String(e),"error"); }
    finally{ setBusy(false); }
  };

  const restore = async(snapId)=>{
    if(!sid || !snapId) return;
    setBusy(true);
    try {
      await api(`/api/sandbox/${encodeURIComponent(sid)}/restore`, {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({snapshot_id: snapId})});
      await refreshResults();
      say(`Restored snapshot ${snapId}`, "ok");
    } catch(e){ say(e.message||String(e),"error"); }
    finally{ setBusy(false); }
  };

  const onUpload = async(ev)=>{
    const f = ev.target.files && ev.target.files[0];
    if(!f || !sid) return;
    setUploading(true);
    try {
      const fd = new FormData(); fd.append("file", f);
      await api(`/api/sandbox/${encodeURIComponent(sid)}/upload`, {method:"POST", body: fd});
      await refreshResults();
      say(`Uploaded ${f.name}`, "ok");
    } catch(e){ say(e.message||String(e),"error"); }
    finally{ setUploading(false); ev.target.value = ""; }
  };

  const distros = caps?.linux?.distros || ["ubuntu:22.04","kalilinux/kali-rolling","remnux/remnux","local-shell"];
  const execs = (results?.recent_events || []).filter(e=>e.kind==="exec").slice(-12).reverse();
  const files = results?.files || [];
  const snaps = results?.snapshots || [];

  return (
    <div style={{display:"grid",gap:10}}>
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",gap:8}}>
        <div className="side-title" style={{fontSize:12,display:"flex",alignItems:"center",gap:6}}><Icon name="shield" size={14}/> Sandbox Environments</div>
        <button className="btn sm ghost" onClick={refreshCaps} title="Refresh capabilities">↻</button>
      </div>

      <div style={{display:"flex",gap:6}}>
        {["linux","windows"].map(k=>(
          <button key={k} className={`btn sm ${tab===k?"":"ghost"}`} onClick={()=>setTab(k)} style={{textTransform:"uppercase"}}>{k}</button>
        ))}
        <div style={{marginLeft:"auto",display:"flex",alignItems:"center",gap:6,fontSize:11,color:"var(--muted,#9aa)"}}>
          backend: <b style={{color:"#fff"}}>{session?.backend || (tab==="linux"?caps?.linux?.backend:caps?.windows?.backend) || "—"}</b>
          {session ? pill(session.status) : pill("idle")}
        </div>
      </div>

      <div className="panel" style={{padding:10,display:"grid",gap:8,border:"1px solid rgba(204,0,0,.25)",background:"rgba(10,0,0,.35)"}}>
        <div style={{fontSize:11,color:"var(--muted,#9aa)"}}>
          Linux: {caps?.linux?.backend || "…"} {caps?.linux?.features?.docker_container?"(Docker)":"(fallback)"} · Windows: {caps?.windows?.backend || "…"} (isolated workspace)
        </div>
        <div style={{display:"flex",gap:8,flexWrap:"wrap",alignItems:"center"}}>
          {tab==="linux" && (
            <select value={distro} onChange={e=>setDistro(e.target.value)} className="input" style={{minWidth:180}}>
              {distros.map(d=> <option key={d} value={d}>{d}</option>)}
            </select>
          )}
          {tab==="windows" && (
            <select value={shell} onChange={e=>setShell(e.target.value)} className="input" style={{minWidth:140}}>
              <option value="powershell">PowerShell</option>
              <option value="cmd">cmd.exe</option>
            </select>
          )}
          <button className="btn sm" onClick={start} disabled={busy || (session && session.status==="running")}>Start</button>
          <button className="btn sm danger" onClick={destroy} disabled={busy || !sid || session?.status==="destroyed"}>Stop / Destroy</button>
          {sid && <span style={{fontSize:11,color:"#cbd5e1"}}>id: <code>{sid}</code></span>}
        </div>

        <div style={{display:"grid",gap:6}}>
          <label style={{fontSize:11,color:"var(--muted,#9aa)"}}>Command / execution</label>
          <textarea className="input" rows={3} value={cmd} onChange={e=>setCmd(e.target.value)} placeholder={tab==="linux"?"e.g. ls -la /workspace":"e.g. Get-ChildItem; whoami"} style={{width:"100%",fontFamily:"var(--font-mono,monospace)"}} />
          <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
            <button className="btn sm" onClick={run} disabled={busy || !sid || session?.status==="destroyed"}>Run</button>
            <label className={`btn sm ghost ${(!sid||uploading)?"disabled":""}`} style={{cursor:(!sid||uploading)?"not-allowed":"pointer"}}>
              {uploading?"Uploading…":"Upload file"}
              <input type="file" style={{display:"none"}} onChange={onUpload} disabled={!sid||uploading} />
            </label>
            <input className="input" placeholder="Snapshot note" value={note} onChange={e=>setNote(e.target.value)} style={{flex:"1 1 160px"}} />
            <button className="btn sm ghost" onClick={snapshot} disabled={busy || !sid}>Snapshot</button>
            <button className="btn sm ghost" onClick={()=>{refreshResults();refreshStatus();}} disabled={!sid}>Refresh</button>
          </div>
        </div>
      </div>

      <div style={{display:"grid",gap:8}}>
        <div className="side-title" style={{fontSize:11}}>Execution results</div>
        {!sid && <div className="muted" style={{fontSize:12}}>Start a sandbox session to execute commands, upload artifacts, and capture results.</div>}
        {execs.length>0 && execs.map((e,i)=>(
          <div key={i} style={{border:"1px solid rgba(204,0,0,.2)",borderRadius:8,padding:8,background:"rgba(0,0,0,.3)"}}>
            <div style={{display:"flex",justifyContent:"space-between",gap:8,fontSize:11,color:"#cbd5e1"}}>
              <span style={{fontFamily:"var(--font-mono,monospace)"}}>$ {String(e.command||"").slice(0,120)}</span>
              <span style={{color:e.ok?"#22c55e":"#f87171"}}>{e.ok?"ok":"err"} · {e.duration_ms||0}ms</span>
            </div>
            {e.stdout ? <pre style={{margin:"6px 0 0",whiteSpace:"pre-wrap",fontSize:11,maxHeight:140,overflow:"auto",color:"#e5e7eb"}}>{String(e.stdout).slice(-4000)}</pre> : null}
            {e.stderr ? <pre style={{margin:"6px 0 0",whiteSpace:"pre-wrap",fontSize:11,maxHeight:100,overflow:"auto",color:"#fca5a5"}}>{String(e.stderr).slice(-2000)}</pre> : null}
          </div>
        ))}
      </div>

      <div style={{display:"grid",gap:6}}>
        <div className="side-title" style={{fontSize:11}}>Workspace files / artifacts</div>
        <div style={{fontSize:11,color:"var(--muted,#9aa)"}}>files: {files.length} · artifacts: {(results?.artifacts||[]).length} · snapshots: {snaps.length}</div>
        {files.length>0 && <div style={{maxHeight:120,overflow:"auto",fontSize:11,border:"1px solid rgba(255,255,255,.06)",borderRadius:6,padding:6}}>
          {files.slice(0,40).map((f,i)=><div key={i} style={{display:"flex",justifyContent:"space-between",gap:8}}><span>{f.path}</span><span style={{color:"#94a3b8"}}>{f.size}B</span></div>)}
        </div>}
        {snaps.length>0 && <div style={{display:"grid",gap:4}}>
          {snaps.slice(-6).reverse().map(s=>(
            <div key={s.id} style={{display:"flex",alignItems:"center",justifyContent:"space-between",gap:8,fontSize:11,border:"1px solid rgba(255,255,255,.06)",borderRadius:6,padding:"4px 6px"}}>
              <span><b>{s.id}</b> · {s.file_count} files {s.note?`· ${s.note}`:""}</span>
              <button className="btn sm ghost" onClick={()=>restore(s.id)} disabled={busy || !sid}>Restore</button>
            </div>
          ))}
        </div>}
      </div>
    </div>
  );
}
