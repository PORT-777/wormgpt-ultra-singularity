// @ts-nocheck
import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import Icon from "./Icon.jsx";

const I = {
  pencil: (p)=><path {...p} d="M12 20h9M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4 12.5-12.5z"/>,
  copy: (p)=><><rect {...p} x="9" y="9" width="13" height="13" rx="2"/><path {...p} d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></>,
  pin: (p)=><path {...p} d="M14 3l7 7-3 1-4 4v5l-2-2-5 5v-3l5-5-2-2h5l4-4 1-3z"/>,
  unpin: (p)=><><path {...p} d="M14 3l7 7-3 1-4 4v5l-2-2-5 5v-3l5-5-2-2h5l4-4 1-3z"/><path {...p} d="M3 3l18 18"/></>,
  trash: (p)=><><path {...p} d="M3 6h18"/><path {...p} d="M8 6V4h8v2"/><path {...p} d="M19 6l-1 14H6L5 6"/><path {...p} d="M10 11v6M14 11v6"/></>,
};
const Svg = ({n,size=15}) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{I[n]?.({})||<circle cx="12" cy="12" r="2"/>}</svg>;

export default function SessionContextMenu({ anchor, session, onClose, onRename, onDuplicate, onPin, onDelete }) {
  const ref = useRef(null);
  const [pos, setPos] = useState({ top: -9999, left: -9999 });
  const [focus, setFocus] = useState(0);
  const pinned = !!session?.pinned;
  const items = [
    { id: "rename", label: "Rename", icon: "pencil", run: () => onRename(session) },
    { id: "duplicate", label: "Duplicate", icon: "copy", run: () => onDuplicate(session) },
    { id: "pin", label: pinned ? "Unpin" : "Pin", icon: pinned ? "unpin" : "pin", run: () => onPin(session) },
    { id: "delete", label: "Delete", icon: "trash", danger: true, run: () => onDelete(session) },
  ];

  useLayoutEffect(() => {
    const el = ref.current; if (!el || !anchor) return;
    const m = 8, vw = window.innerWidth, vh = window.innerHeight;
    const r = el.getBoundingClientRect();
    let left = anchor.left;
    let top = anchor.bottom + 4;
    if (left + r.width > vw - m) left = Math.max(m, vw - r.width - m);
    if (left < m) left = m;
    if (top + r.height > vh - m) top = Math.max(m, anchor.top - r.height - 4); // flip up
    if (top < m) top = m;
    setPos({ top, left });
  }, [anchor, session]);

  useEffect(() => {
    const onDown = (e) => { if (ref.current && !ref.current.contains(e.target)) onClose(); };
    const onKey = (e) => {
      if (e.key === "Escape") { e.preventDefault(); onClose(); }
      else if (e.key === "ArrowDown") { e.preventDefault(); setFocus((f) => (f + 1) % items.length); }
      else if (e.key === "ArrowUp") { e.preventDefault(); setFocus((f) => (f - 1 + items.length) % items.length); }
      else if (e.key === "Enter") { e.preventDefault(); items[focus]?.run(); onClose(); }
    };
    window.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    window.addEventListener("scroll", onClose, true);
    window.addEventListener("resize", onClose);
    return () => { window.removeEventListener("mousedown", onDown); window.removeEventListener("keydown", onKey); window.removeEventListener("scroll", onClose, true); window.removeEventListener("resize", onClose); };
  }, [onClose, items, focus]);

  useEffect(() => { const btn = ref.current?.querySelector(`[data-idx="${focus}"]`); btn?.focus?.(); }, [focus, pos]);

  if (!anchor || !session) return null;
  return createPortal(
    <div ref={ref} className="sctx-menu" role="menu" aria-label="Session actions" style={{ top: pos.top, left: pos.left }}>
      {items.map((it, i) => (
        <button key={it.id} type="button" role="menuitem" data-idx={i} tabIndex={i === focus ? 0 : -1}
          className={`sctx-item${it.danger ? " danger" : ""}`}
          onClick={() => { it.run(); onClose(); }}
          onMouseEnter={() => setFocus(i)}>
          <span className="sctx-ico"><Svg n={it.icon} size={15} /></span>
          <span>{it.label}</span>
        </button>
      ))}
    </div>,
    document.body
  );
}
