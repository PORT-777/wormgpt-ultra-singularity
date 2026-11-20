// @ts-nocheck
import React from "react";
import Icon from "./Icon.jsx";

const STATE = {
  planning: { label: "Planning", live: true },
  thinking: { label: "Thinking", live: true },
  executing_tool: { label: "Executing", live: true },
  reflecting: { label: "Reflecting", live: true },
  sleeping: { label: "Idle", live: false },
  error: { label: "Error", live: false },
};

export default function StatusBar({ status = {}, fullAccess = false }) {
  const meta = STATE[status.state] || STATE.sleeping;
  const providers = Object.entries(status.providers || {});
  return (
    <div style={{display:"flex", alignItems:"center", gap:8, flexWrap:"wrap"}}>
      {fullAccess && <span className="pill live"><Icon name="shield" size={12}/> Full Access</span>}
      <span className={`pill ${meta.live ? "live" : ""}`} title={`State: ${status.state||"sleeping"}`}>
        <span className={`dot ${meta.live?"run":status.state==="error"?"":"ok"}`} style={status.state==="error"?{background:"var(--danger)"}:undefined}></span>
        {meta.label}
      </span>
      <span className="pill" title="Model route"><Icon name="spark" size={12}/>{status.route || "auto"}</span>
      {!!providers.length && <span className="pill" title={providers.map(([k,v])=>`${k}:${v?"ok":"off"}`).join(", ")}>
        {providers.filter(([,v])=>v).length}/{providers.length} providers
      </span>}
    </div>
  );
}
