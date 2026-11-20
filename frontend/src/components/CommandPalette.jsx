// @ts-nocheck
import React, { useEffect, useMemo, useRef, useState } from "react";
import Icon from "./Icon.jsx";

function score(text, q) {
  const t = String(text || "").toLowerCase();
  const s = String(q || "").trim().toLowerCase();
  if (!s) return 1;
  if (t === s) return 100;
  if (t.startsWith(s)) return 80;
  if (t.includes(s)) return 60;
  let i = 0;
  for (const ch of t) if (ch === s[i]) i++;
  return i === s.length ? 40 : 0;
}

export default function CommandPalette({ open, onClose, commands = [] }) {
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    setQ("");
    setActive(0);
    const t = setTimeout(() => inputRef.current?.focus(), 0);
    return () => clearTimeout(t);
  }, [open]);

  const items = useMemo(() => {
    const filtered = commands
      .map((c) => ({ c, s: score(`${c.label} ${c.hint || ""} ${c.group || ""}`, q) }))
      .filter((x) => x.s > 0)
      .sort((a, b) => b.s - a.s || String(a.c.label).localeCompare(String(b.c.label), "ar"));
    return filtered.map((x) => x.c);
  }, [commands, q]);

  useEffect(() => { setActive(0); }, [q, open]);

  useEffect(() => {
    if (!open) return;
    const el = listRef.current?.querySelector(`[data-idx="${active}"]`);
    el?.scrollIntoView({ block: "nearest" });
  }, [active, open, items.length]);

  if (!open) return null;

  const run = (cmd) => {
    if (!cmd) return;
    onClose();
    Promise.resolve().then(() => cmd.run?.());
  };

  const onKeyDown = (e) => {
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); onClose(); }
    else if (e.key === "ArrowDown") { e.preventDefault(); setActive((i) => Math.min(i + 1, Math.max(0, items.length - 1))); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((i) => Math.max(i - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); run(items[active]); }
  };

  return (
    <div className="overlay palette-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="palette" role="dialog" aria-modal="true" aria-label="لوحة الأوامر" onKeyDown={onKeyDown}>
        <div className="palette-head">
          <Icon name="search" size={16} />
          <input ref={inputRef} className="palette-input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="اكتب أمراً أو اسم جلسة... (↑↓ Enter Esc)" aria-label="بحث الأوامر" />
          <kbd className="kbd">Esc</kbd>
        </div>
        <div className="palette-list" ref={listRef} role="listbox" aria-label="نتائج الأوامر">
          {!items.length && <div className="panel-state" style={{ margin: 8 }}><div className="title">لا توجد نتائج.</div><div className="muted">جرّب: جلسة، إعدادات، trace، terminal، تحديث، أو اسم جلسة.</div></div>}
          {items.map((cmd, idx) => (
            <button key={cmd.id || `${cmd.label}-${idx}`} type="button" data-idx={idx} role="option" aria-selected={idx === active}
              className={`palette-item ${idx === active ? "active" : ""}`} onMouseEnter={() => setActive(idx)} onClick={() => run(cmd)}>
              <span className="palette-icon"><Icon name={cmd.icon || "spark"} size={15} /></span>
              <span className="palette-main">
                <span className="palette-label">{cmd.label}</span>
                {cmd.hint && <span className="palette-hint">{cmd.hint}</span>}
              </span>
              {cmd.group && <span className="kbd" style={{ marginLeft: "auto" }}>{cmd.group}</span>}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
