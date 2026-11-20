// @ts-nocheck
import React, { useState } from "react";
import Icon from "../components/Icon.jsx";
import Markdown from "../components/Markdown.jsx";
import { CheckpointChips } from "../components/CheckpointUI.jsx";
import { t } from "./i18n.js";

function fmtTime(ts) {
  const n = Number(ts);
  if (!n) return "";
  const d = new Date(n < 1e12 ? n * 1000 : n);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function Message({
  m,
  index,
  onCopy,
  onFeedback,
  onRegenerate,
  onEdit,
  onRetry,
  onOpenContext,
  sessionId,
  toast,
  onAfterRevert,
  running,
}) {
  const [copied, setCopied] = useState(false);
  const [vote, setVote] = useState(0);
  const isUser = m?.role === "user";
  const content = String(m?.content ?? "");
  const failed = !!m?.failed;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
      onCopy?.(content);
    } catch { /* clipboard unavailable */ }
  };

  const doVote = (v) => {
    setVote(v);
    onFeedback?.(m, index, v);
  };

  return (
    <div className={`msg2 ${isUser ? "user" : "assistant"}`}>
      <div className="msg-avatar">{isUser ? <Icon name="user" size={14} /> : <Icon name="spark" size={14} />}</div>

      <div className="msg-main">
        <div className="msg-head">
          <span className="who">{isUser ? t("أنت", "You") : "🔥😈 PORT 777 EVIL ☠️🔥👹"}</span>
          {!isUser && <span className="tag">AI</span>}
          {m?.ts ? <span>{fmtTime(m.ts)}</span> : null}
        </div>

        <div className={`bubble2 ${failed ? "failed" : ""}`}>
          {isUser
            ? <div style={{ whiteSpace: "pre-wrap" }}>{content}</div>
            : <Markdown text={content} />}
        </div>

        {!isUser && !!m?.checkpoints?.length && (
          <div style={{ marginTop: 2 }}>
            <CheckpointChips message={m} sessionId={sessionId} toast={toast} onAfterRevert={onAfterRevert} />
          </div>
        )}

        {!isUser && !!m?.sources?.length && (
          <div className="src-row" style={{ marginTop: 4, display: "flex", flexWrap: "wrap", gap: 4, alignItems: "center" }}>
            <span style={{ fontSize: 11, opacity: 0.7 }}>{t("المصادر", "Sources")}:</span>
            {m.sources.slice(-8).map((s, i) => (
              <a key={s.url || i} href={s.url} target="_blank" rel="noreferrer"
                 className="src-chip" title={s.url}
                 style={{ fontSize: 11, padding: "1px 6px", borderRadius: 999, border: "1px solid var(--border)", textDecoration: "none", maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {s.title || s.url}
              </a>
            ))}
          </div>
        )}

        {!isUser && m?.vision?.ok && (
          <details style={{ marginTop: 4, fontSize: 12 }}>
            <summary style={{ cursor: "pointer", opacity: 0.85 }}>
              👁 {t("تحليل الصورة", "Image analysis")} · {m.vision.provider}/{m.vision.model}
            </summary>
            <pre style={{ whiteSpace: "pre-wrap", marginTop: 4, opacity: 0.85 }}>{m.vision.text}</pre>
          </details>
        )}

        <div className="msg-actions">
          <button type="button" className="mini-btn" onClick={copy} title={t("نسخ", "Copy")}>
            <Icon name={copied ? "check" : "copy"} size={12} />{copied ? t("تم النسخ", "Copied") : t("نسخ", "Copy")}
          </button>

          {isUser && onEdit && (
            <button type="button" className="mini-btn" onClick={() => onEdit(content)} title={t("تعديل وإعادة الإرسال", "Edit & resend")}>
              <Icon name="edit" size={12} />{t("تعديل", "Edit")}
            </button>
          )}

          {!isUser && !running && (
            <button type="button" className="mini-btn" onClick={() => onRegenerate?.()} title={t("إعادة توليد الرد", "Regenerate response")}>
              <Icon name="refresh" size={12} />{t("إعادة", "Retry")}
            </button>
          )}

          {!isUser && (
            <>
              <button type="button" className={`mini-btn ${vote === 1 ? "on" : ""}`} onClick={() => doVote(1)} title={t("رد جيد", "Good response")}>
                <Icon name="thumbUp" size={12} />
              </button>
              <button type="button" className={`mini-btn ${vote === -1 ? "on" : ""}`} onClick={() => doVote(-1)} title={t("رد سيئ", "Bad response")}>
                <Icon name="thumbDown" size={12} />
              </button>
            </>
          )}

          <button type="button" className="mini-btn" onClick={onOpenContext} title={t("التفاصيل", "Details")}>
            <Icon name="panelRight" size={12} />{t("التفاصيل", "Details")}
          </button>
        </div>
      </div>
    </div>
  );
}