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
  const data = ct.includes("application/json") ? await res.json().catch(()=>null) : await res.text().catch(()=>null);
  if (!res.ok) {
    const msg = (data && (data.detail || data.error || data.message)) || (typeof data === "string" ? data : `HTTP ${res.status}`);
    const e = new Error(String(msg)); e.data = data; throw e;
  }
  return data;
}
const runSec = (action, params={}) => api("/api/security/run", { method:"POST", body: JSON.stringify({ action, params }) });

function copyText(t, notify){ navigator.clipboard?.writeText(String(t||"")).then(()=>notify?.("Copied","ok")).catch(()=>notify?.("Copy failed","error")); }
function download(name, content, type="text/plain;charset=utf-8"){ const a=document.createElement("a"); a.href=URL.createObjectURL(new Blob([content||""],{type})); a.download=name; document.body.appendChild(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(a.href),800); }

const box = {border:"1px solid rgba(204,0,0,.25)", background:"rgba(10,0,0,.35)", borderRadius:10, padding:10};
const label = {fontSize:11, color:"var(--muted,#9aa)", marginBottom:4};
const ta = {width:"100%", minHeight:120, fontFamily:"var(--font-mono,monospace)", fontSize:12};
const pre = {margin:0, whiteSpace:"pre-wrap", wordBreak:"break-word", fontSize:11, maxHeight:260, overflow:"auto", fontFamily:"var(--font-mono,monospace)"};

function IOCPanel({ notify }){
  const [text,setText]=useState("");
  const [result,setResult]=useState(null);
  const [busy,setBusy]=useState(false);
  const [q,setQ]=useState("");
  const extract = async()=>{
    if(!text.trim()) return notify?.("Provide input text/logs","warn");
    setBusy(true);
    try{ setResult(await runSec("iocs",{text})); notify?.("IOCs extracted","ok"); try{ emitXp("ioc_extracted"); }catch{} }
    catch(e){ notify?.(e.message||String(e),"error"); }
    finally{ setBusy(false); }
  };
  const cats = result?.categories || {};
  const rows = useMemo(()=>{
    const out=[];
    Object.entries(cats).forEach(([type,vals])=>{
      (Array.isArray(vals)?vals:[]).forEach(v=>{ if(v!=null && String(v)!=="") out.push({type, value:String(v)}); });
    });
    const qq=q.trim().toLowerCase();
    return qq ? out.filter(r=>r.type.toLowerCase().includes(qq)||r.value.toLowerCase().includes(qq)) : out;
  },[cats,q]);
  const exportFmt = async(fmt)=>{
    try{
      const r = await runSec("ioc_export",{text, fmt});
      const content = r?.content ?? JSON.stringify(r, null, 2);
      const name = r?.filename || `iocs.${fmt==="csv"?"csv":fmt==="stix"?"json":"txt"}`;
      download(name, typeof content==="string"?content:JSON.stringify(content,null,2), fmt==="json"||fmt==="stix"?"application/json":"text/plain;charset=utf-8");
    }catch(e){ notify?.(e.message||String(e),"error"); }
  };
  return <div style={{display:"grid",gap:10}}>
    <div style={box}>
      <div style={label}>Input (text / logs, defanged supported: hxxp://, [.], [@])</div>
      <textarea className="input" style={ta} value={text} onChange={e=>setText(e.target.value)} placeholder="Paste text, logs, or indicators..." />
      <div style={{display:"flex",gap:8,flexWrap:"wrap",marginTop:8}}>
        <button className="btn sm" onClick={extract} disabled={busy}>{busy?"Extracting...":"Extract IOCs"}</button>
        <button className="btn sm ghost" onClick={()=>exportFmt("json")} disabled={!text.trim()}>Export JSON</button>
        <button className="btn sm ghost" onClick={()=>exportFmt("csv")} disabled={!text.trim()}>Export CSV</button>
        <button className="btn sm ghost" onClick={()=>exportFmt("stix")} disabled={!text.trim()}>Export STIX</button>
        <button className="btn sm ghost" onClick={()=>exportFmt("text")} disabled={!text.trim()}>Export TXT</button>
      </div>
    </div>
    <div style={box}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",gap:8,marginBottom:8}}>
        <div className="side-title" style={{fontSize:11}}>Results {result?`· ${result.count||rows.length} indicators`:""}</div>
        <input className="input" style={{maxWidth:220}} placeholder="Filter type/value..." value={q} onChange={e=>setQ(e.target.value)} />
      </div>
      {!result && <div className="muted" style={{fontSize:12}}>Run extraction to see IOC table.</div>}
      {result && <div style={{overflow:"auto",maxHeight:320}}>
        <table style={{width:"100%",borderCollapse:"collapse",fontSize:12}}>
          <thead><tr style={{textAlign:"left",color:"#fca5a5"}}>
            <th style={{padding:"6px 8px",borderBottom:"1px solid rgba(204,0,0,.25)"}}>Type</th>
            <th style={{padding:"6px 8px",borderBottom:"1px solid rgba(204,0,0,.25)"}}>Value</th>
            <th style={{padding:"6px 8px",borderBottom:"1px solid rgba(204,0,0,.25)"}}>Actions</th>
          </tr></thead>
          <tbody>
            {rows.length===0 && <tr><td colSpan={3} style={{padding:10,color:"var(--muted,#9aa)"}}>No indicators found.</td></tr>}
            {rows.map((r,i)=>(<tr key={i}>
              <td style={{padding:"6px 8px",borderBottom:"1px solid rgba(255,255,255,.05)",color:"#f87171",whiteSpace:"nowrap"}}>{r.type}</td>
              <td style={{padding:"6px 8px",borderBottom:"1px solid rgba(255,255,255,.05)",fontFamily:"var(--font-mono,monospace)",wordBreak:"break-all"}}>{r.value}</td>
              <td style={{padding:"6px 8px",borderBottom:"1px solid rgba(255,255,255,.05)"}}>
                <button className="btn sm ghost" onClick={()=>copyText(r.value,notify)}>Copy</button>
              </td>
            </tr>))}
          </tbody>
        </table>
      </div>}
    </div>
  </div>;
}

function YaraPanel({ notify }){
  const [text,setText]=useState("");
  const [name,setName]=useState("");
  const [description,setDescription]=useState("");
  const [rule,setRule]=useState("");
  const [meta,setMeta]=useState(null);
  const [sample,setSample]=useState("");
  const [scan,setScan]=useState(null);
  const [busy,setBusy]=useState(false);
  const [err,setErr]=useState("");
  const generate = async()=>{
    if(!text.trim() && !description.trim()) return notify?.("Provide strings/description","warn");
    setBusy(true); setErr("");
    try{
      const r = await runSec("yara_generate",{ text, description: description||text, name: name||undefined });
      const ruleText = typeof r?.rule === "string" ? r.rule : (r?.yaml || JSON.stringify(r?.rule||r,null,2));
      setRule(ruleText||""); setMeta(r); notify?.("YARA rule generated","ok"); try{ emitXp("yara_generated"); }catch{}
    }catch(e){ setErr(e.message||String(e)); notify?.(e.message||String(e),"error"); }
    finally{ setBusy(false); }
  };
  const scanNow = async()=>{
    if(!rule.trim()) return notify?.("Generate or paste a rule first","warn");
    setBusy(true); setErr("");
    try{
      const r = await runSec("yara_scan",{ rule_text: rule, text: sample || text || "" });
      setScan(r); notify?.("Scan complete","ok");
    }catch(e){ setErr(e.message||String(e)); notify?.(e.message||String(e),"error"); }
    finally{ setBusy(false); }
  };
  return <div style={{display:"grid",gap:10}}>
    <div style={box}>
      <div style={{display:"grid",gap:8,gridTemplateColumns:"1fr 1fr"}}>
        <div><div style={label}>Rule name (optional)</div><input className="input" value={name} onChange={e=>setName(e.target.value)} placeholder="Suspicious_PS_Downloader" /></div>
        <div><div style={label}>Behavior description</div><input className="input" value={description} onChange={e=>setDescription(e.target.value)} placeholder="Detect PowerShell downloader..." /></div>
      </div>
      <div style={{marginTop:8}}><div style={label}>Strings / sample text</div><textarea className="input" style={{...ta,minHeight:90}} value={text} onChange={e=>setText(e.target.value)} placeholder="Indicators, strings, or sample content..." /></div>
      <div style={{display:"flex",gap:8,flexWrap:"wrap",marginTop:8}}>
        <button className="btn sm" onClick={generate} disabled={busy}>{busy?"Working...":"Generate YARA"}</button>
        <button className="btn sm ghost" onClick={()=>download(`${(name||'rule').replace(/[^A-Za-z0-9_-]+/g,'_')}.yar`, rule)} disabled={!rule}>Export .yar</button>
        <button className="btn sm ghost" onClick={()=>copyText(rule,notify)} disabled={!rule}>Copy rule</button>
      </div>
      {err && <div style={{marginTop:8,color:"#f87171",fontSize:12}}>{err}</div>}
    </div>
    <div style={box}>
      <div style={label}>YARA rule (editable)</div>
      <textarea className="input" style={{...ta,minHeight:220,fontFamily:"var(--font-mono,monospace)"}} value={rule} onChange={e=>setRule(e.target.value)} placeholder="Generated rule will appear here..." />
    </div>
    <div style={box}>
      <div style={label}>Validate / test against sample text</div>
      <textarea className="input" style={{...ta,minHeight:80}} value={sample} onChange={e=>setSample(e.target.value)} placeholder="Paste sample/content to scan (defaults to strings input)..." />
      <div style={{display:"flex",gap:8,marginTop:8}}><button className="btn sm ghost" onClick={scanNow} disabled={busy || !rule.trim()}>Test rule</button></div>
      {scan && <pre style={{...pre,marginTop:8}}>{JSON.stringify(scan,null,2)}</pre>}
    </div>
  </div>;
}

function SigmaPanel({ notify }){
  const [text,setText]=useState("");
  const [title,setTitle]=useState("");
  const [target,setTarget]=useState("all");
  const [rule,setRule]=useState("");
  const [conversions,setConversions]=useState(null);
  const [validation,setValidation]=useState(null);
  const [busy,setBusy]=useState(false);
  const generate = async()=>{
    if(!text.trim()) return notify?.("Describe behavior first","warn");
    setBusy(true);
    try{
      const r = await runSec("sigma_generate",{ text, description:text, title: title||undefined, target });
      const ruleText = r?.yaml || (typeof r?.rule === "string" ? r.rule : JSON.stringify(r?.rule||r,null,2));
      setRule(ruleText||"");
      setConversions(r?.conversions || null);
      setValidation(null);
      notify?.("Sigma rule generated","ok");
      try{ emitXp("sigma_generated"); }catch{}
    }catch(e){ notify?.(e.message||String(e),"error"); }
    finally{ setBusy(false); }
  };
  const convert = async()=>{
    if(!rule.trim()) return notify?.("Rule required","warn");
    setBusy(true);
    try{ const r = await runSec("sigma_convert",{ rule_text: rule, target }); setConversions(r?.conversions || r); notify?.("Converted","ok"); }
    catch(e){ notify?.(e.message||String(e),"error"); }
    finally{ setBusy(false); }
  };
  const validate = async()=>{
    if(!rule.trim()) return notify?.("Rule required","warn");
    setBusy(true);
    try{ setValidation(await runSec("sigma_validate",{ rule_text: rule })); notify?.("Validation complete","ok"); }
    catch(e){ notify?.(e.message||String(e),"error"); }
    finally{ setBusy(false); }
  };
  const convEntries = conversions && typeof conversions === "object" ? Object.entries(conversions) : [];
  return <div style={{display:"grid",gap:10}}>
    <div style={box}>
      <div style={label}>Behavior description (Arabic or English)</div>
      <input className="input" value={title} onChange={e=>setTitle(e.target.value)} placeholder="Optional title" style={{marginBottom:8}} />
      <textarea className="input" style={{...ta,minHeight:100}} value={text} onChange={e=>setText(e.target.value)} placeholder="Describe suspicious behavior, command lines, process/network events..." />
      <div style={{display:"flex",gap:8,flexWrap:"wrap",marginTop:8,alignItems:"center"}}>
        <select className="input" value={target} onChange={e=>setTarget(e.target.value)} style={{maxWidth:220}}>
          <option value="all">All targets</option><option value="splunk">Splunk (SPL)</option><option value="kql">Sentinel (KQL)</option><option value="eql">Elastic (EQL)</option><option value="aql">QRadar (AQL)</option>
        </select>
        <button className="btn sm" onClick={generate} disabled={busy}>{busy?"Working...":"Generate Sigma"}</button>
        <button className="btn sm ghost" onClick={convert} disabled={busy || !rule.trim()}>Convert</button>
        <button className="btn sm ghost" onClick={validate} disabled={busy || !rule.trim()}>Validate</button>
        <button className="btn sm ghost" onClick={()=>copyText(rule,notify)} disabled={!rule}>Copy YAML</button>
      </div>
    </div>
    <div style={box}>
      <div style={label}>Sigma rule (editable YAML)</div>
      <textarea className="input" style={{...ta,minHeight:220}} value={rule} onChange={e=>setRule(e.target.value)} placeholder="Generated Sigma YAML..." />
      {validation && <pre style={{...pre,marginTop:8}}>{JSON.stringify(validation,null,2)}</pre>}
    </div>
    {convEntries.length>0 && <div style={box}>
      <div className="side-title" style={{fontSize:11,marginBottom:8}}>Conversions</div>
      <div style={{display:"grid",gap:8}}>
        {convEntries.map(([k,v])=>(
          <div key={k} style={{border:"1px solid rgba(255,255,255,.06)",borderRadius:8,padding:8}}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:6}}>
              <b style={{fontSize:12,color:"#fca5a5",textTransform:"uppercase"}}>{k}</b>
              <button className="btn sm ghost" onClick={()=>copyText(typeof v==="string"?v:JSON.stringify(v,null,2),notify)}>Copy</button>
            </div>
            <pre style={pre}>{typeof v==="string"?v:JSON.stringify(v,null,2)}</pre>
          </div>
        ))}
      </div>
    </div>}
  </div>;
}

function MitrePanel({ notify }){
  const [catalog,setCatalog]=useState(null);
  const [observed,setObserved]=useState("");
  const [mapRes,setMapRes]=useState(null);
  const [busy,setBusy]=useState(false);
  const [selected,setSelected]=useState(null);
  useEffect(()=>{ (async()=>{ try{ setCatalog(await api("/api/security/mitre/catalog")); }catch(e){ /* ignore */ } })(); },[]);
  const mapNow = async()=>{
    if(!observed.trim()) return notify?.("Provide behavior/text to map","warn");
    setBusy(true);
    try{ setMapRes(await runSec("mitre",{ text: observed })); notify?.("Mapped to ATT&CK","ok"); }
    catch(e){ notify?.(e.message||String(e),"error"); }
    finally{ setBusy(false); }
  };
  const hitIds = new Set((mapRes?.techniques||[]).map(t=>t.id));
  const confById = Object.fromEntries((mapRes?.techniques||[]).map(t=>[t.id,t.confidence||0]));
  const tactics = catalog?.tactics || [];
  const by = catalog?.by_tactic || {};
  return <div style={{display:"grid",gap:10}}>
    <div style={box}>
      <div style={label}>Observed behavior / telemetry (text) to map onto MITRE ATT&CK</div>
      <textarea className="input" style={{...ta,minHeight:90}} value={observed} onChange={e=>setObserved(e.target.value)} placeholder="e.g. powershell -enc ..., scheduled task persistence, C2 over HTTPS..." />
      <div style={{display:"flex",gap:8,marginTop:8,flexWrap:"wrap"}}>
        <button className="btn sm" onClick={mapNow} disabled={busy}>{busy?"Mapping...":"Map to ATT&CK"}</button>
        {mapRes && <span style={{fontSize:12,color:"#fca5a5"}}>{(mapRes.techniques||[]).length} techniques detected</span>}
      </div>
    </div>
    <div style={box}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8}}>
        <div className="side-title" style={{fontSize:11}}>MITRE ATT&CK Matrix (Enterprise)</div>
        <div style={{fontSize:10,color:"var(--muted,#9aa)"}}><span style={{color:"#ff4d4d"}}>■</span> observed <span style={{color:"#4a0b0b",marginLeft:8}}>■</span> not observed</div>
      </div>
      {!catalog && <div className="muted" style={{fontSize:12}}>Loading catalog...</div>}
      {catalog && <div style={{overflow:"auto"}}>
        <div style={{display:"grid",gridTemplateColumns:`repeat(${Math.max(tactics.length,1)}, minmax(140px,1fr))`,gap:8,minWidth:Math.max(900,tactics.length*150)}}>
          {tactics.map(tac=>(
            <div key={tac} style={{display:"grid",gap:6,alignContent:"start"}}>
              <div style={{fontSize:11,fontWeight:700,color:"#fff",padding:"6px 8px",border:"1px solid rgba(204,0,0,.35)",borderRadius:8,background:"rgba(204,0,0,.12)",textAlign:"center"}}>{tac}</div>
              {(by[tac]||[]).map(tech=>{
                const hit = hitIds.has(tech.id);
                const conf = confById[tech.id] || 0;
                return <button key={tech.id} onClick={()=>setSelected({...tech, tactic:tac, confidence:conf, hit})} title={`${tech.id} ${tech.name}`} style={{textAlign:"left",cursor:"pointer",padding:"6px 7px",borderRadius:7,border:`1px solid ${hit?"rgba(255,0,0,.7)":"rgba(204,0,0,.18)"}`,background: hit?`rgba(204,0,0,${0.18 + Math.min(0.45, conf/200)})`:"rgba(20,0,0,.35)",color: hit?"#fff":"#cbd5e1",boxShadow: hit?"0 0 14px rgba(204,0,0,.25)":"none"}}>
                  <div style={{fontSize:10,color: hit?"#fecaca":"#f87171"}}>{tech.id}</div>
                  <div style={{fontSize:11,lineHeight:1.25}}>{tech.name}</div>
                  {hit && <div style={{fontSize:10,marginTop:2,color:"#ffb4b4"}}>{conf}%</div>}
                </button>;
              })}
            </div>
          ))}
        </div>
      </div>}
      {selected && <div style={{marginTop:10,padding:10,border:"1px solid rgba(204,0,0,.3)",borderRadius:8,background:"rgba(0,0,0,.35)"}}>
        <div style={{display:"flex",justifyContent:"space-between",gap:8}}><b style={{color:"#fff"}}>{selected.id} — {selected.name}</b><button className="btn sm ghost" onClick={()=>setSelected(null)}>Close</button></div>
        <div style={{fontSize:12,color:"#cbd5e1",marginTop:4}}>Tactic: {selected.tactic} {selected.hit?`· Confidence: ${selected.confidence}%`:"· Not observed in current mapping"}</div>
        {selected.description ? <div style={{fontSize:12,marginTop:6,color:"#e5e7eb"}}>{selected.description}</div> : null}
      </div>}
    </div>
  </div>;
}

export default function SecurityToolsPanel({ notify }){
  const [sub,setSub]=useState("ioc");
  const tabs=[{id:"ioc",label:"IOC Extractor",icon:"search"},{id:"yara",label:"YARA",icon:"code"},{id:"sigma",label:"Sigma / Query",icon:"terminal"},{id:"mitre",label:"MITRE ATT&CK",icon:"activity"}];
  return <div style={{display:"grid",gap:12}}>
    <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",gap:8,flexWrap:"wrap"}}>
      <div className="side-title" style={{fontSize:12,display:"flex",alignItems:"center",gap:6}}><Icon name="shield" size={14}/> Security Tools</div>
      <div style={{fontSize:11,color:"var(--muted,#9aa)"}}>IOC · YARA · Sigma · MITRE (local CyberOps)</div>
    </div>
    <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
      {tabs.map(t=>(
        <button key={t.id} className={`btn sm ${sub===t.id?"":"ghost"}`} onClick={()=>setSub(t.id)}>
          <Icon name={t.icon} size={13}/> {t.label}
        </button>
      ))}
    </div>
    {sub==="ioc" && <IOCPanel notify={notify} />}
    {sub==="yara" && <YaraPanel notify={notify} />}
    {sub==="sigma" && <SigmaPanel notify={notify} />}
    {sub==="mitre" && <MitrePanel notify={notify} />}
  </div>;
}
