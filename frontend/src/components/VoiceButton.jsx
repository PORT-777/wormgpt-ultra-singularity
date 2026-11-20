// @ts-nocheck
import React, { useEffect, useRef, useState } from "react";
import Icon from "./Icon.jsx";
import { t } from "../ui/i18n.js";

export default function VoiceButton({ onText, disabled = false }) {
  const [listening, setListening] = useState(false);
  const [supported, setSupported] = useState(true);
  const recognitionRef = useRef(null);
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);

  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { setSupported(false); return; }
    const rec = new SR();
    rec.lang = "ar-EG"; rec.interimResults = false; rec.continuous = false;
    rec.onresult = (e) => { const text = Array.from(e.results).map(r=>r[0].transcript).join(" ").trim(); if (text) onText(text); };
    rec.onend = () => setListening(false); rec.onerror = () => setListening(false);
    recognitionRef.current = rec;
    return () => { try { rec.abort(); } catch {} };
  }, [onText]);

  if (!supported) {
    const toggleRec = async () => {
      if (listening) { try { mediaRef.current?.stop(); } catch {} setListening(false); return; }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const rec = new MediaRecorder(stream); chunksRef.current = [];
        rec.ondataavailable = (e) => chunksRef.current.push(e.data);
        rec.onstop = async () => {
          stream.getTracks().forEach(t => t.stop());
          const fd = new FormData(); fd.append("file", new Blob(chunksRef.current, { type:"audio/webm" }), "speech.webm");
          try { const r = await fetch("/api/transcribe", { method:"POST", body: fd }); const d = await r.json(); if (d.ok && d.text && !String(d.text).startsWith("ERROR")) onText(d.text); } catch {}
        };
        rec.start(); mediaRef.current = rec; setTimeout(()=>rec.state==="recording" && rec.stop(), 12000); setListening(true);
      } catch {}
    };
    return <button type="button" onClick={toggleRec} disabled={disabled} title={t("الإدخال الصوتي", "Voice input")} className={`btn sm ${listening?"danger":"ghost"}`}><Icon name="mic" size={14}/>{listening ? t("إصغاء", "Rec") : t("مايك", "Mic")}</button>;
  }

  const toggle = () => {
    if (listening) { recognitionRef.current?.stop(); setListening(false); }
    else { try { recognitionRef.current?.start(); setListening(true); } catch {} }
  };
  return <button type="button" onClick={toggle} disabled={disabled} title={t("الإدخال الصوتي", "Voice input")} className={`btn sm ${listening?"danger":"ghost"}`}><Icon name="mic" size={14}/>{listening ? t("إيقاف", "Stop") : t("مايك", "Mic")}</button>;
}
