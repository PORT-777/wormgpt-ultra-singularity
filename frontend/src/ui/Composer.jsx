// @ts-nocheck
import React, { useEffect, useRef, useState } from "react";
import Icon from "../components/Icon.jsx";
import ModePicker, { MODE_PLACEHOLDERS } from "../components/ModePicker.jsx";
import VoiceButton from "../components/VoiceButton.jsx";
import ModelMenu from "./ModelMenu.jsx";
import { t } from "./i18n.js";
import { useAnchoredPanel } from "./useAnchoredPanel.js";

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
  const [toolsOpen, setToolsOpen] = useState(false);
  const toolsRef = useRef(null);
  const toolsPos = useAnchoredPanel(toolsOpen, toolsRef, { width: 268 });
  const [envOpen, setEnvOpen] = useState(false);
  const envRef = useRef(null);
  const envPos = useAnchoredPanel(envOpen, envRef, { width: 300 });
  useEffect(() => {
    if (!envOpen) return;
    const onDoc = (e) => { if (envRef.current && !envRef.current.contains(e.target)) setEnvOpen(false); };
    const onKey = (e) => { if (e.key === "Escape") setEnvOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onKey); };
  }, [envOpen]);

  const execLabel = execEnv === "off"
    ? t("محادثة فقط", "Chat only")
    : ((execEnvs.find(e => e.id === execEnv)?.label) || execEnv);
  const execOn = execEnv && execEnv !== "off";

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(240, Math.max(52, el.scrollHeight)) + "px";
  }, [value, ref]);

  useEffect(() => {
    if (!toolsOpen) return;
    const onDoc = (e) => { if (toolsRef.current && !toolsRef.current.contains(e.target)) setToolsOpen(false); };
    const onKey = (e) => { if (e.key === "Escape") setToolsOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onKey); };
  }, [toolsOpen]);

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

            <div ref={toolsRef} style={{ position: "relative" }}>
              <button
                type="button"
                className={`tool-btn ${toolsOpen ? "on" : ""}`}
                title={t("الأدوات", "Tools")}
                onClick={() => setToolsOpen(v => !v)}
              >
                <Icon name="wand" size={15} />
                <span className="lbl">{t("الأدوات", "Tools")}</span>
              </button>
              {toolsOpen && (
                <div className="menu" style={toolsPos} role="menu">
                  <div className="menu-label">{t("القدرات", "Capabilities")}</div>
                  <button type="button" className="menu-item" onClick={() => { fileRef.current?.click(); setToolsOpen(false); }}>
                    <span className="mi-ico"><Icon name="paperclip" size={14} /></span>{t("إضافة ملفات", "Add files")}<span className="mi-tail">{t("صور، PDF، نص", "images, pdf, text")}</span>
                  </button>
                  <button type="button" className="menu-item" onClick={() => { onAdvanced?.("models"); setToolsOpen(false); }}>
                    <span className="mi-ico"><Icon name="layers" size={14} /></span>{t("الموديلات والمزودون", "Models & providers")}
                  </button>
                  <button type="button" className="menu-item" onClick={() => { onAdvanced?.("agents"); setToolsOpen(false); }}>
                    <span className="mi-ico"><Icon name="bot" size={14} /></span>{t("تشغيل وكيل", "Run an agent")}
                  </button>
                  <div className="menu-sep" />
                  <div className="menu-label">{t("الجلسة", "Session")}</div>
                  <button type="button" className="menu-item" onClick={() => { onFullAccess?.(!fullAccess); setToolsOpen(false); }}>
                    <span className="mi-ico"><Icon name={fullAccess ? "shield" : "lock"} size={14} /></span>
                    {fullAccess ? t("الوصول الكامل: مفعّل", "Full access: on") : t("الوصول الكامل: متوقف", "Full access: off")}
                  </button>
                  <button type="button" className="menu-item" onClick={() => { onVoiceReplies?.(!voiceReplies); setToolsOpen(false); }}>
                    <span className="mi-ico"><Icon name="volume" size={14} /></span>
                    {t("الرد الصوتي", "Spoken replies")}: {voiceReplies ? t("مفعّل", "on") : t("متوقف", "off")}
                  </button>
                  <button type="button" className="menu-item" onClick={() => { onClear?.(); setToolsOpen(false); }}>
                    <span className="mi-ico"><Icon name="trash" size={14} /></span>{t("مسح المحادثة", "Clear conversation")}
                  </button>
                </div>
              )}
            </div>

            <div ref={envRef} style={{ position: "relative" }}>
              <button
                type="button"
                className={`tool-btn ${execOn ? "on" : ""}`}
                title={t("بيئة التنفيذ", "Execution environment")}
                onClick={() => setEnvOpen(v => !v)}
              >
                <Icon name="terminal" size={15} />
                <span className="lbl">{execLabel}</span>
                {execOn && <span className="tag" style={{ marginLeft: 4 }}>live</span>}
              </button>
              {envOpen && (
                <div className="menu" style={envPos} role="menu">
                  <div className="menu-label">{t("بيئة التنفيذ", "Execution environment")}</div>
                  <button type="button" className="menu-item" onClick={() => { onExecEnv?.("off"); setEnvOpen(false); }}>
                    <span className="mi-ico"><Icon name="chat" size={14} /></span>{t("محادثة فقط", "Chat only")}
                  </button>
                  {(execEnvs || []).map(e => (
                    <button
                      key={e.id}
                      type="button"
                      className="menu-item"
                      disabled={!e.available}
                      style={{ opacity: e.available ? 1 : 0.5 }}
                      title={e.detail || e.label}
                      onClick={() => {
                        if (!e.available) { onToast?.(`${e.label}: ${e.detail || "unavailable"}`, "warn"); return; }
                        onExecEnv?.(e.id); setEnvOpen(false);
                      }}
                    >
                      <span className="mi-ico"><Icon name="terminal" size={14} /></span>
                      {e.label}
                      <span className="mi-tail">{e.available ? "" : t("غير متاح", "n/a")}</span>
                    </button>
                  ))}
                  {execTask?.id && (
                    <>
                      <div className="menu-sep" />
                      <div className="menu-label">{t("المهمة النشطة", "Active task")}: {execTask.id}</div>
                      <button type="button" className="menu-item" onClick={() => { onOpenExec?.(); setEnvOpen(false); }}>
                        <span className="mi-ico"><Icon name="panelRight" size={14} /></span>{t("إدارة التنفيذ", "Manage execution")}
                      </button>
                    </>
                  )}
                  {!execTask?.id && (
                    <>
                      <div className="menu-sep" />
                      <button type="button" className="menu-item" onClick={() => { onOpenExec?.(); setEnvOpen(false); }}>
                        <span className="mi-ico"><Icon name="panelRight" size={14} /></span>{t("تفاصيل البيئة", "Environment details")}
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>

            <ModePicker value={mode} onChange={onMode} />
            <ModelMenu value={model} onChange={onModel} onToast={onToast} />

            <span className="spacer" />
            <VoiceButton
              disabled={running}
              onText={(txt) => { onChange?.(String(value || "") + (value ? " " : "") + txt); ref.current?.focus(); }}
            />
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