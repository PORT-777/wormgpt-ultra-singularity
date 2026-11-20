// @ts-nocheck
import React from "react";
import Icon from "./Icon.jsx";
export default function Terminal({logs=[],termRef,running=false,expanded=false}){
  return <div className="term"><div className="term-head"><div className="row"><Icon name="terminal" size={14}/> Tool execution log</div><span className={`pill ${running?"live":""}`}>{running?"live":`${logs.length} lines`}</span></div><div ref={termRef} className={`term-body ${expanded?"expanded":""}`}>{logs.length?logs.map((l,i)=><div key={i}>{l}</div>):<div className="muted">[init] tool/output logs stream here from existing backend events.</div>}{running && <div style={{color:"var(--accent)"}}>_</div>}</div></div>;
}
