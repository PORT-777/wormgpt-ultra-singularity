// @ts-nocheck
import React, { useEffect, useRef, useState } from "react";
import Icon from "../components/Icon.jsx";
import ModePicker, { MODE_PLACEHOLDERS } from "../components/ModePicker.jsx";
import { t } from "./i18n.js";

export default function Composer({
  value,
  onChange,
  onSend,
  running,
  onStop,
  model,
  onModel,
  mode,
  onMode,
  execEnv = "off",
  onExecEnv,
  execEnvs = [],
  execTask = null,
  onOpenExec,
  attachments = [],
  onAttach,
  onRemoveAttachment,
  onToast,
  fullAccess,
  onFullAccess,
  voiceReplies,
  onVoiceReplies,
  onAdvanced,
  onClear,
  inputRef,
  disabled,
  hint = t("Enter للإرسال · Shift+Enter لسطر جديد", "Enter to send · Shift+Enter for a new line"),
}) {
  const localRef = useRef(null);
  const ref = inputRef || localRef;
  const fileRef = useRef(null);
  const [drag, setDrag] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(240, Math.max(52, el.scrollHeight)) + "px";
  }, [value, ref]);

  const canSend = !!String(value || "").trim() && !running && !disabled;
  const submit = () => { if (canSend) onSend?.(); };

  const pickFiles = (files) => {
    const arr = Array.from(files || []);
    if (arr.length) onAttach?.(arr);
  };

  return (
    <div className="composer-wrap">
      <div className="composer-inner">
        <form
          className={`composer2 ${drag ? "drag" : ""}`}
          onSubmit={(e) => { e.preventDefault(); submit(); }}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); pickFiles(e.dataTransfer?.files); }}
        >
          <textarea
            ref={ref}
            value={value}
            onChange={(e) => onChange?.(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent?.isComposing) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder={running ? t("جارٍ العمل… اضغط Esc للإيقاف", "Working… press Esc to stop") : (MODE_PLACEHOLDERS[mode] || t("اكتب رسالة إلى PORT 777…", "Message PORT 777…"))}
            aria-label={t("الرسالة", "Message")}
            rows={1}
          />

          {!!attachments.length && (
            <div className="attach-strip">
              {attachments.map((a, i) => (
                <span key={`${a.name}-${i}`} className={`attach-chip ${a.ok ? "" : "err"}`} title={a.error || a.name}>
                  <Icon name={a.ok ? "file" : "alert"} size={12} />
                  <span className="nm">{a.name}</span>
                  <button type="button" className="x" onClick={() => onRemoveAttachment?.(i)} aria-label={`Remove ${a.name}`}>
                    <Icon name="close" size={11} />
                  </button>
                </span>
              ))}
            </div>
          )}

          <div className="composer-bar">
            <input ref={fileRef} type="file" multiple hidden onChange={(e) => { pickFiles(e.target.files); e.target.value = ""; }} />

            <button type="button" className="tool-btn" title={t("إرفاق ملفات", "Attach files")} onClick={() => fileRef.current?.click()}>
              <Icon name="paperclip" size={16} />
            </button>

            <ModePicker value={mode} onChange={onMode} />

            <span className="spacer" />
            {running ? (
              <button type="button" className="send-btn stop" onClick={onStop} title={t("إيقاف التوليد (Esc)", "Stop generating (Esc)")}>
                <Icon name="stop" size={15} />
              </button>
            ) : (
              <button type="submit" className="send-btn" disabled={!canSend} title={canSend ? "Send" : "Type a message"}>
                <Icon name="arrowUp" size={17} />
              </button>
            )}
          </div>
        </form>
        <div className="composer-hint">
          {running ? t("جارٍ التوليد — يمكنك الإيقاف في أي وقت", "Generating — you can stop at any time") : <>{hint}</>}
          {fullAccess ? t(" · الوصول الكامل مفعّل", " · Full access enabled") : ""}
        </div>
      </div>
    </div>
  );
}