// @ts-nocheck
import React, { useEffect, useMemo, useRef, useState } from "react";
import Icon from "../components/Icon.jsx";
import { LANGUAGES, t } from "./i18n.js";

function timeAgo(ts) {
  const ms = Number(ts) || 0;
  if (!ms) return "";
  const s = Math.max(1, Math.floor(Date.now() / 1000 - ms));
  if (s < 60) return t("الآن", "just now");
  if (s < 3600) return t(`قبل ${Math.floor(s / 60)} د`, `${Math.floor(s / 60)}m ago`);
  if (s < 86400) return t(`قبل ${Math.floor(s / 3600)} س`, `${Math.floor(s / 3600)}h ago`);
  if (s < 604800) return t(`قبل ${Math.floor(s / 86400)} ي`, `${Math.floor(s / 86400)}d ago`);
  return new Date(ms * 1000).toLocaleDateString();
}

function bucket(ts) {
  const ms = Number(ts) || 0;
  if (!ms) return "older";
  const now = new Date();
  const d = new Date(ms * 1000);
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime() / 1000;
  if (ms >= startToday) return "today";
  if (ms >= startToday - 86400) return "yesterday";
  if (ms >= startToday - 7 * 86400) return "week";
  if (ms >= startToday - 30 * 86400) return "month";
  return "older";
}

const GROUPS = [
  ["pinned", t("مثبّتة", "Pinned")],
  ["today", t("اليوم", "Today")],
  ["yesterday", t("أمس", "Yesterday")],
  ["week", t("آخر 7 أيام", "Previous 7 days")],
  ["month", t("آخر 30 يومًا", "Previous 30 days")],
  ["older", t("أقدم", "Older")],
];

const NAV = [];

export default function Sidebar({
  sessions = [],
  activeId,
  onSelect,
  onNew,
  onRename,
  onPin,
  onDelete,
  onDuplicate,
  onOpen,
  onSettings,
  onToggleTheme,
  theme = "dark",
  lang = "ar",
  onLang,
  onCollapse,
  userLabel = "Operator",
  disconnected = false,
}) {
  const [q, setQ] = useState("");
  const [menu, setMenu] = useState(null);
  const [editing, setEditing] = useState(null);
  const [draft, setDraft] = useState("");
  const rootRef = useRef(null);

  useEffect(() => {
    if (!menu) return;
    const close = (e) => { if (!e.target.closest(".conv-menu")) setMenu(null); };
    const esc = (e) => { if (e.key === "Escape") setMenu(null); };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", esc); };
  }, [menu]);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    const list = (Array.isArray(sessions) ? sessions : []).filter(x => x && x.id);
    if (!s) return list;
    return list.filter(x => `${x.title || ""} ${x.id || ""}`.toLowerCase().includes(s));
  }, [sessions, q]);

  const groups = useMemo(() => {
    const out = {};
    for (const it of filtered) {
      const b = it.pinned ? "pinned" : bucket(it.created);
      (out[b] = out[b] || []).push(it);
    }
    for (const k of Object.keys(out)) out[k].sort((a, b) => (Number(b.created) || 0) - (Number(a.created) || 0));
    return out;
  }, [filtered]);

  const startRename = (s) => { setEditing(s.id); setDraft(s.title || ""); setMenu(null); };
  const commitRename = () => {
    if (editing && draft.trim()) onRename?.(editing, draft.trim());
    setEditing(null);
  };

  const openMenu = (e, s) => {
    e.stopPropagation();
    const r = e.currentTarget.getBoundingClientRect();
    setMenu({ s, x: Math.min(r.left, window.innerWidth - 220), y: Math.min(r.bottom + 4, window.innerHeight - 280) });
  };

  const renderConv = (s) => (
    <div
      key={s.id}
      className={`conv-row ${s.id === activeId ? "active" : ""}`}
      role="button"
      tabIndex={0}
      onClick={() => onSelect?.(s.id)}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect?.(s.id); } }}
      title={s.title || s.id}
    >
      <div className="conv-main">
        {editing === s.id ? (
          <input
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onClick={(e) => e.stopPropagation()}
            onBlur={commitRename}
            onKeyDown={(e) => {
              if (e.key === "Enter") { e.preventDefault(); commitRename(); }
              if (e.key === "Escape") setEditing(null);
            }}
            style={{ width: "100%", height: 24, border: "1px solid var(--accent-40)", borderRadius: 6, background: "var(--bg)", padding: "0 6px", fontSize: 12.5 }}
          />
        ) : (
          <>
            <div className="conv-title">
              {s.pinned ? <span className="pin-dot" title="Pinned"><Icon name="pin" size={11} /></span> : null}{" "}
              {s.title || t("محادثة بدون عنوان", "Untitled conversation")}
            </div>
            <div className="conv-meta">{timeAgo(s.created)}{s.n ? ` · ${s.n} msg` : ""}</div>
          </>
        )}
      </div>
      {editing !== s.id && (
        <div className="conv-actions">
          <button type="button" className="conv-act" title="More actions" onClick={(e) => openMenu(e, s)}><Icon name="more" size={14} /></button>
        </div>
      )}
    </div>
  );

  return (
    <aside className="sidebar2" ref={rootRef} aria-label="Main navigation">
      <div className="side-brand">
        <div className="brand-mark" aria-hidden="true">P7</div>
        <div className="brand-txt">
          <div className="brand-name">🔥😈 PORT 777 EVIL ☠️🔥👹</div>
          <div className="brand-sub">{t("مساحة الذكاء", "AI Workspace")}</div>
        </div>
        {onCollapse && (
          <button type="button" className="icon-btn side-collapse" title="Hide sidebar (Ctrl+/)" onClick={onCollapse}>
            <Icon name="sidebar" size={16} />
          </button>
        )}
      </div>

      <button type="button" className="side-new" onClick={() => onNew?.()}>
        <Icon name="plus" size={15} /> {t("محادثة جديدة", "New chat")}
        <kbd>Ctrl K</kbd>
      </button>

      <div className="side-search">
        <span className="ico"><Icon name="search" size={14} /></span>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t("ابحث في المحادثات…", "Search conversations…")}
          aria-label="Search conversations"
        />
      </div>

      <div className="side-scroll">
        {!q && (
          <>
            <div className="side-group" style={{ marginTop: 2 }}>
              {NAV.map(n => (
                <button key={n.id} type="button" className="side-item" onClick={() => onOpen?.(n.id)}>
                  <span className="ico"><Icon name={n.icon} size={16} /></span>
                  {n.label}
                </button>
              ))}
            </div>
            <div className="side-label" style={{ marginTop: 14 }}>{t("المحادثات", "Conversations")}</div>
          </>
        )}

        {q && <div className="side-label">{t(`${filtered.length} نتيجة`, `${filtered.length} result${filtered.length === 1 ? "" : "s"}`)}</div>}

        {GROUPS.map(([key, label]) => {
          const items = groups[key];
          if (!items || !items.length) return null;
          return (
            <div className="side-group" key={key}>
              <div className="side-label">{label}<span className="count">{items.length}</span></div>
              {items.map(renderConv)}
            </div>
          );
        })}

        {!filtered.length && (
          <div className="ctx-empty" style={{ paddingTop: 26 }}>
            {q ? t("لا توجد محادثات تطابق بحثك.", "No conversations match your search.") : t("لا توجد محادثات بعد.\nابدأ محادثة جديدة لتظهر هنا.", "No conversations yet.\nStart a new chat to see it here.")}
          </div>
        )}
      </div>

      <div className="side-foot">
        <button type="button" className="side-item" onClick={() => onToggleTheme?.()}>
          <span className="ico"><Icon name={theme === "light" ? "moon" : "sun"} size={16} /></span>
          {theme === "light" ? t("الوضع الداكن", "Dark mode") : t("الوضع الفاتح", "Light mode")}
        </button>
        {onLang && (
          <label className="side-item lang-select" title={t("اللغة", "Language")}>
            <span className="ico"><Icon name="globe" size={16} /></span>
            <select value={lang} onChange={(e) => onLang?.(e.target.value)} aria-label={t("اللغة", "Language")}>
              {LANGUAGES.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
            </select>
          </label>
        )}
        <button type="button" className="side-item" onClick={() => onSettings?.()}>
          <span className="ico"><Icon name="settings" size={16} /></span>
          {t("الإعدادات", "Settings")}
        </button>
        <div className="side-user">
          <span className="avatar2">{String(userLabel || "OP").slice(0, 2).toUpperCase()}</span>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 12.5, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{userLabel}</div>
            <div style={{ fontSize: 10.5, color: disconnected ? "var(--err)" : "var(--muted)" }}>
              {disconnected ? t("غير متصل", "Offline") : t("مساحة محلية", "Local workspace")}
            </div>
          </div>
        </div>
      </div>

      {menu && (
        <div className="menu conv-menu" style={{ position: "fixed", left: menu.x, top: menu.y }} role="menu">
          <button type="button" className="menu-item" onClick={() => startRename(menu.s)}><span className="mi-ico"><Icon name="edit" size={14} /></span>{t("إعادة تسمية", "Rename")}</button>
          <button type="button" className="menu-item" onClick={() => { onPin?.(menu.s.id, !menu.s.pinned); setMenu(null); }}>
            <span className="mi-ico"><Icon name="pin" size={14} /></span>{menu.s.pinned ? t("إلغاء التثبيت", "Unpin") : t("تثبيت في الأعلى", "Pin to top")}
          </button>
          <button type="button" className="menu-item" onClick={() => { onDuplicate?.(menu.s.id); setMenu(null); }}><span className="mi-ico"><Icon name="copy" size={14} /></span>{t("نسخ", "Duplicate")}</button>
          <button type="button" className="menu-item" onClick={() => { onOpen?.("export", menu.s.id); setMenu(null); }}><span className="mi-ico"><Icon name="download" size={14} /></span>{t("تصدير", "Export")}</button>
          <div className="menu-sep" />
          <button type="button" className="menu-item danger" onClick={() => { onDelete?.(menu.s.id); setMenu(null); }}><span className="mi-ico"><Icon name="trash" size={14} /></span>{t("حذف", "Delete")}</button>
        </div>
      )}
    </aside>
  );
}