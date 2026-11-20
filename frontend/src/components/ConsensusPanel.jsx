// @ts-nocheck
import React, { useCallback, useRef, useState } from "react";
import Icon from "./Icon.jsx";
import Markdown from "./Markdown.jsx";

const ROUTES = [
  { id: "local", label: "المحلي", icon: "cpu" },
  { id: "groq", label: "Groq", icon: "zap" },
  { id: "gemini", label: "Gemini", icon: "sparkle" },
  { id: "hf", label: "HuggingFace", icon: "bot" },
];

const EMPTY_VARIANT = {
  text: "",
  done: false,
  error: "",
  route: "",
  chars: 0,
};

export default function ConsensusPanel({ notify, sessionId }) {
  const [task, setTask] = useState("");
  const [running, setRunning] = useState(false);
  const [variants, setVariants] = useState(
    ROUTES.map((r) => ({ ...EMPTY_VARIANT, route: r.id })),
  );
  const [consensus, setConsensus] = useState("");
  const [consensusDone, setConsensusDone] = useState(false);
  const [openRoutes, setOpenRoutes] = useState(
    ROUTES.map((r) => r.id),
  );
  const abortRef = useRef(null);

  const allDone = () =>
    variants.every((v) => v.done || v.error) && variants.length > 0;

  const reset = useCallback(() => {
    setVariants(
      ROUTES.map((r) => ({ ...EMPTY_VARIANT, route: r.id })),
    );
    setConsensus("");
    setConsensusDone(false);
  }, []);

  const appendVariant = useCallback((seq, route, chunk) => {
    setVariants((vs) =>
      vs.map((v) => {
        if (v.route !== route) return v;
        return { ...v, text: v.text + chunk, done: v.done };
      }),
    );
  }, []);

  const runConsensus = useCallback(async () => {
    const t = (task || "").trim();
    if (!t || running) return;
    reset();
    setRunning(true);
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      const res = await fetch("/api/consensus", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: t,
          session_id: sessionId || "",
          routes: openRoutes,
          mode: "code",
        }),
        signal: ctrl.signal,
      });
      if (!res.ok) {
        const txt = await res.text().catch(() => res.statusText);
        throw new Error(`HTTP ${res.status}: ${txt.slice(0, 200)}`);
      }
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop() ?? "";
        for (const p of parts) {
          if (!p.startsWith("data:")) continue;
          try {
            const ev = JSON.parse(p.replace(/^data:\s*/, ""));
            const { type, data, variant, route } = ev || {};
            if (type === "variant_start") {
              setVariants((vs) =>
                vs.map((v) =>
                  v.route === route ? { ...v, done: false, error: "" } : v,
                ),
              );
            } else if (type === "stream") {
              if (route) {
                setVariants((vs) =>
                  vs.map((v) =>
                    v.route === route
                      ? { ...v, text: (v.text || "") + (data || "") }
                      : v,
                  ),
                );
              }
            } else if (type === "variant_done") {
              setVariants((vs) =>
                vs.map((v) =>
                  v.route === route
                    ? { ...v, done: true, chars: data && data.chars }
                    : v,
                ),
              );
              if (allDone() && !consensusDone) {
                // consensus will arrive as variant route="consensus"
              }
            } else if (type === "final" && route === "consensus") {
              setConsensus(typeof data === "string" ? data : String(data || ""));
              setConsensusDone(true);
            } else if (type === "error") {
              setVariants((vs) =>
                vs.map((v) =>
                  v.route === route
                    ? { ...v, done: true, error: String(data || "") }
                    : v,
                ),
              );
            }
          } catch { /* ignore malformed SSE lines */ }
        }
      }
    } catch (err) {
      if (err.name !== "AbortError") {
        notify(`Consensus failed: ${err.message}`, "error");
        setRunning(false);
      }
    } finally {
      if (!abortRef.current || abortRef.current.signal.aborted) {
        setRunning(false);
        abortRef.current = null;
      }
    }
  }, [task, running, sessionId, openRoutes, reset, consensusDone, notify]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setRunning(false);
  }, []);

  const copyVariant = async (route) => {
    const v = variants.find((x) => x.route === route);
    if (!v || !v.text) return;
    try {
      await navigator.clipboard.writeText(v.text);
      notify(`تم نسخ مخرج ${route}`, "ok");
    } catch { notify("تعذر النسخ", "error"); }
  };

  const copyConsensus = async () => {
    if (!consensus) return;
    try {
      await navigator.clipboard.writeText(consensus);
      notify("تم نسخ الإجماع", "ok");
    } catch { notify("تعذر النسخ", "error"); }
  };

  const variantCard = (v) => {
    const routeInfo = ROUTES.find((r) => r.id === v.route);
    const active = running && !v.done && !v.error;
    return (
      <div
        key={v.route}
        className={`cv-card ${v.done ? "done" : ""} ${
          v.error ? "err" : ""
        } ${active ? "streaming" : ""}`}
      >
        <div className="cv-head">
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <Icon name={routeInfo ? routeInfo.icon : "bot"} size={13} />
            <span className="cv-title">{routeInfo ? routeInfo.label : v.route}</span>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            {active && (
              <span className="cv-dot" />
            )}
            {v.done && !v.error && (
              <button
                type="button"
                className="mini-btn"
                onClick={() => copyVariant(v.route)}
                title="نسخ"
              >
                <Icon name="copy" size={12} />
              </button>
            )}
            {v.error && (
              <span className="cv-dot" style={{ background: "var(--err)" }} />
            )}
          </div>
        </div>
        <div className="cv-body">
          {v.error ? (
            <div className="cv-err">
              <Icon name="alert" size={13} /> {v.error}
            </div>
          ) : v.text || active ? (
            <div className="cv-stream" dir="auto">
              <Markdown text={v.text} />
              {active && <span className="cursor" />}
            </div>
          ) : (
            <div className="cv-empty">{trans("انتظار…", "Waiting…")}</div>
          )}
        </div>
        {v.done && !v.error && v.chars && (
          <div className="cv-foot">{v.chars} حرفاً · {v.chars} chars</div>
        )}
      </div>
    );
  };

  const gridStyle = {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
    gap: 10,
  };

  return (
    <div className="cv-panel">
      <div className="cv-head-bar">
        <div className="cv-title-row">
          <Icon name="layers" size={16} style={{ marginRight: 6 }} />
          <span className="cv-main-title">
            {trans("التوافق متعدد الموديلات", "Multi-Model Consensus")}
          </span>
          <span className="cv-sub">
            {trans("مخرجات جنبًا إلى جنب + إجماع مركب", "Side-by-side variants + synthesized consensus")}
          </span>
        </div>
        <div className="cv-actions">
          <label className="cv-chip">
            <input
              type="checkbox"
              checked={openRoutes.includes("local")}
              onChange={(e) => {
                setOpenRoutes((o) =>
                  e.target.checked ? [...o, "local"] : o.filter((x) => x !== "local"),
                );
              }}
            />
            محلي
          </label>
          <label className="cv-chip">
            <input
              type="checkbox"
              checked={openRoutes.includes("groq")}
              onChange={(e) => {
                setOpenRoutes((o) =>
                  e.target.checked ? [...o, "groq"] : o.filter((x) => x !== "groq"),
                );
              }}
            />
            Groq
          </label>
          <label className="cv-chip">
            <input
              type="checkbox"
              checked={openRoutes.includes("gemini")}
              onChange={(e) => {
                setOpenRoutes((o) =>
                  e.target.checked ? [...o, "gemini"] : o.filter((x) => x !== "gemini"),
                );
              }}
            />
            Gemini
          </label>
          <label className="cv-chip">
            <input
              type="checkbox"
              checked={openRoutes.includes("hf")}
              onChange={(e) => {
                setOpenRoutes((o) =>
                  e.target.checked ? [...o, "hf"] : o.filter((x) => x !== "hf"),
                );
              }}
            />
            HF
          </label>
        </div>
      </div>

      <div className="cv-input-row">
        <textarea
          className="cv-input"
          placeholder={trans("أكتب المهمة… سيتم تشغيلها على الموديلات المختارة جنبًا إلى جنب", "Write the task… it runs on selected models side by side")}
          value={task}
          onChange={(e) => setTask(e.target.value)}
          rows={3}
        />
        <div className="cv-btns">
          <button
            type="button"
            className={`btn ${running ? "ghost" : "primary"}`}
            disabled={running || !task.trim()}
            onClick={runConsensus}
          >
            {running ? <Icon name="stop" size={13} /> ` إيقاف` : <Icon name="spark" size={13} /> ` تشغيل الإجماع`}
          </button>
          {!running && consensusDone && consensus && (
            <button type="button" className="btn sm" onClick={copyConsensus}>
              <Icon name="copy" size={12} /> نسخ الإجماع
            </button>
          )}
        </div>
      </div>

      <div className="cv-grid" style={gridStyle}>
        {variants.map(variantCard)}
      </div>

      {consensusDone && consensus && (
        <div className="cv-consensus">
          <div className="cv-head">
            <span className="cv-title">
              <Icon name="brain" size={14} style={{ marginRight: 6 }} />
              {trans("الإجماع المركب", "Synthesized Consensus")}
            </span>
            <button type="button" className="mini-btn" onClick={copyConsensus}>
              <Icon name="copy" size={12} /> نسخ
            </button>
          </div>
          <div className="cv-body" dir="auto">
            <Markdown text={consensus} />
          </div>
        </div>
      )}
    </div>
  );
}

function trans(ar, en) {
  // simple language hook — return Arabic if document lang is ar, else English
  try {
    return document.documentElement.lang === "ar" ? ar : en;
  } catch {
    return en;
  }
}
