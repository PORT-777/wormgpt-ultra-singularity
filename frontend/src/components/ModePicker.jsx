// @ts-nocheck
import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import Icon from "./Icon.jsx";
import { useAnchoredPanel } from "../ui/useAnchoredPanel.js";

export const MODES = [
  { id:"code",  label:"Code",  icon:"terminal", color:"var(--accent)",     desc:"كتابة وتعديل الكود وتنفيذ المهام" },
  { id:"plan",  label:"Plan",  icon:"activity", color:"#f59e0b",            desc:"يخطط خطوات المهمة قبل التنفيذ" },
  { id:"ask",   label:"Ask",   icon:"chat",     color:"var(--ok,#22c55e)",  desc:"شرح وإجابات بدون تعديل ملفات" },
  { id:"debug", label:"Debug", icon:"search",   color:"#b91c1c",            desc:"تشخيص الأخطاء وإصلاحها" },
];
export const MODE_IDS = MODES.map(m=>m.id);
export const MODE_PLACEHOLDERS = {
  code:  "اسأل، ابنِ، صحّح، افحص الملفات، أو نفّذ مهمة…",
  plan:  "صف المهمة وسأخطط الخطوات قبل التنفيذ…",
  ask:   "اسأل أي سؤال — شرح بدون تعديل ملفات…",
  debug: "صف الخطأ أو السلوك غير المتوقع لتشخيصه…",
};

export default function ModePicker({ value="code", onChange }){
  const [open,setOpen]=useState(false);
  const [active,setActive]=useState(0);
  const rootRef=useRef(null);
  const menuRef=useRef(null);
  const listRef=useRef(null);
  const menuPos = useAnchoredPanel(open, rootRef, { width: 340 });
  const cur = MODES.find(m=>m.id===value) || MODES[0];

  useEffect(()=>{ if(!open) return; const i=Math.max(0, MODES.findIndex(m=>m.id===value)); setActive(i);
    const onDoc=(e)=>{ if(!rootRef.current?.contains(e.target) && !menuRef.current?.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", onDoc); return ()=>document.removeEventListener("mousedown", onDoc);
  },[open,value]);

  useEffect(()=>{ if(open) listRef.current?.querySelector(`[data-idx="${active}"]`)?.scrollIntoView({block:"nearest"}); },[active,open]);

  const choose=(id)=>{ onChange?.(id); setOpen(false); };

  const onKey=(e)=>{
    if(!open){
      if(e.key==="ArrowDown"||e.key==="Enter"||e.key===" "){ e.preventDefault(); setOpen(true); }
      return;
    }
    if(e.key==="Escape"){ e.preventDefault(); e.stopPropagation(); setOpen(false); }
    else if(e.key==="ArrowDown"){ e.preventDefault(); setActive(i=>Math.min(i+1, MODES.length-1)); }
    else if(e.key==="ArrowUp"){ e.preventDefault(); setActive(i=>Math.max(i-1,0)); }
    else if(e.key==="Enter"){ e.preventDefault(); choose(MODES[active]?.id||value); }
  };

  return (
    <div className="modepick" ref={rootRef} onKeyDown={onKey}>
      <button type="button" className="btn sm ghost modepick-btn" aria-haspopup="listbox" aria-expanded={open} onClick={()=>setOpen(v=>!v)} title="Response mode">
        <span className="modepick-ic" style={{color:cur.color}}><Icon name={cur.icon} size={13}/></span>
        <span>{cur.label}</span>
        <span className="modepick-chev" aria-hidden="true">▾</span>
      </button>
      {open && createPortal(
        <div className="modepick-menu modepick-portal" role="listbox" aria-label="Mode" ref={menuRef} style={{...menuPos, zIndex: 300}}>
          <div ref={listRef}>
            {MODES.map((m,idx)=>(
              <button key={m.id} type="button" data-idx={idx} role="option" aria-selected={m.id===value}
                className={`modepick-item ${m.id===value?"selected":""} ${idx===active?"active":""}`}
                onMouseEnter={()=>setActive(idx)} onClick={()=>choose(m.id)}>
                <span className="modepick-ic lg" style={{color:m.color}}><Icon name={m.icon} size={15}/></span>
                <span className="modepick-main"><span className="modepick-label">{m.label}</span><span className="modepick-desc">{m.desc}</span></span>
                <span className="modepick-check" aria-hidden="true">{m.id===value?"✓":""}</span>
              </button>
            ))}
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
