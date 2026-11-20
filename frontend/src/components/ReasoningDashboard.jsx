// @ts-nocheck
import React, { useState } from "react";
import Icon from "./Icon.jsx";

const LEVEL_LABELS = {
  1: "L1 — Fast",
  2: "L2 — Standard",
  3: "L3 — Deep",
  4: "L4 — Expert",
  5: "L5 — Singularity",
};

const LEVEL_COLORS = {
  1: "#22c55e",
  2: "#3b82f6",
  3: "#8b5cf6",
  4: "#f59e0b",
  5: "#ef4444",
};

export default function ReasoningDashboard({ level, confidence, notes, steps, active }) {
  const [expanded, setExpanded] = useState(false);
  const color = level ? (LEVEL_COLORS[level] || "#9ca3af") : "#9ca3af";
  const label = level ? (LEVEL_LABELS[level] || `L${level}`) : "—";
  const conf = confidence == null ? "—" : `${confidence}%`;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "6px 10px",
          background: "rgba(10,0,0,.35)",
          border: `1px solid ${color}44`,
          borderRadius: 8,
          fontSize: 11.5,
          color: "#eee",
          cursor: steps && steps.length ? "pointer" : "default",
        }}
        title={notes || "Intelligence: reasoning level and verification status"}
        onClick={() => steps && steps.length && setExpanded((v) => !v)}
      >
        <Icon name="spark" size={10} style={{ color }} />
        <span style={{ fontWeight: 600 }}>{label}</span>
        <span style={{ color: "#9aa", fontSize: 10 }}>Confidence:</span>
        <span style={{ fontWeight: 700, color: color }}>{conf}</span>
        {steps && steps.length > 0 && (
          <span style={{ flex: 1 }} />
        )}
        {steps && steps.length > 0 && (
          <span style={{ color: "#9aa", fontSize: 10 }}>
            {expanded ? "▲" : "▼"} {steps.length} step{steps.length !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {expanded && steps && steps.length > 0 && (
        <div
          style={{
            background: "rgba(10,0,0,.5)",
            border: `1px solid ${color}33`,
            borderRadius: 8,
            padding: "8px 10px",
            display: "grid",
            gap: 6,
            maxHeight: 240,
            overflow: "auto",
          }}
        >
          {steps.map((s, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 8,
                fontSize: 11,
                padding: "4px 0",
                borderBottom: "1px solid rgba(255,255,255,.05)",
              }}
            >
              <span
                style={{
                  flex: "0 0 auto",
                  width: 18,
                  height: 18,
                  borderRadius: "50%",
                  background: active === i ? color : "rgba(255,255,255,.08)",
                  color: active === i ? "#fff" : "#9aa",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 10,
                  fontWeight: 700,
                }}
              >
                {active === i ? "●" : i + 1}
              </span>
              <div style={{ minWidth: 0, flex: 1 }}>
                <div style={{ color: "#ddd", fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {s.phase || s.name || `Step ${i + 1}`}
                </div>
                {s.detail && (
                  <div style={{ color: "#9aa", marginTop: 2, lineHeight: 1.4 }}>
                    {String(s.detail).slice(0, 200)}
                  </div>
                )}
                {s.tool && (
                  <div style={{ color: color, marginTop: 2, fontFamily: "monospace", fontSize: 10 }}>
                    ⚡ {s.tool}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}