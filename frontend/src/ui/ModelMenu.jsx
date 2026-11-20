// @ts-nocheck
import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import Icon from "../components/Icon.jsx";
import { gatewayApi } from "../gatewayClient.js";
import { t } from "./i18n.js";

const TEMPLATES = [
  ["auto", "تلقائي", "Auto"],
  ["auto/free", "تلقائي مجاني", "Auto Free"],
  ["auto/fast:free", "سريع (مجاني)", "Fast (free)"],
  ["auto/cheap:free", "اقتصادي (مجاني)", "Cheap (free)"],
  ["auto/smart", "ذكي", "Smart"],
  ["auto/chaos", "فوضوي", "Chaos"],
  ["kilo", "كيلو أيه آي", "Kilo AI"],
];
const TEMPLATE_LABEL = Object.fromEntries(TEMPLATES.map(([id, ar, en]) => [id, { ar, en }]));

export default function ModelMenu({ value, onChange, onToast, compact = false }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [freeOnly, setFreeOnly] = useState(false);
  const [tab, setTab] = useState("mine");
  const [models, setModels] = useState([]);
  const [catalog, setCatalog] = useState({ models: [], total: 0, loading: false });
  const [custom, setCustom] = useState("");
  const [pos, setPos] = useState(null);
  const boxRef = useRef(null);

  // keep the popover inside the viewport (flip above/below, clamp horizontally)
  useLayoutEffect(() => {
    if (!open) { setPos(null); return; }
    const update = () => {
      const el = boxRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const width = Math.min(420, window.innerWidth - 24);
      // align to the button when it fits, otherwise to the opposite edge
      let left = r.left;
      if (left + width > window.innerWidth - 12) left = r.right - width;
      left = Math.min(Math.max(12, left), window.innerWidth - width - 12);
      const spaceAbove = r.top - 12;
      const spaceBelow = window.innerHeight - r.bottom - 12;
      const up = spaceAbove > 320 || spaceAbove >= spaceBelow;
      setPos({
        position: "fixed", left, width, right: "auto",
        top: up ? "auto" : r.bottom + 8,
        bottom: up ? window.innerHeight - r.top + 8 : "auto",
        maxHeight: Math.min(560, Math.max(220, up ? spaceAbove : spaceBelow)),
      });
    };
    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [open]);

  useEffect(() => {
    let alive = true;
    if (!open) return;
    gatewayApi.listModels(freeOnly, true).then(r => {
      if (!alive) return;
      const src = Array.isArray(r.models) ? r.models : [];
      setModels(src.filter(m => m && m.provider_enabled !== false && m.model_enabled !== false && !m.cooldown));
    }).catch(() => alive && setModels([]));
    return () => { alive = false; };
  }, [open, freeOnly]);

  useEffect(() => {
    if (!open || tab !== "catalog" || catalog.models.length || catalog.loading) return;
    setCatalog(c => ({ ...c, loading: true }));
    gatewayApi.listCatalog(q, "", freeOnly, 300, 0)
      .then(r => setCatalog({ models: r.models || [], total: r.total || 0, loading: false }))
      .catch(e => { setCatalog({ models: [], total: 0, loading: false }); onToast?.("Model catalog: " + e.message, "warn"); });
  }, [open, tab]); // eslint-disable-line

  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => { if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onKey); };
  }, [open]);

  const list = useMemo(() => {
    const s = q.trim().toLowerCase();
    const src = tab === "catalog"
      ? (catalog.models || []).map(m => ({ model: m.id, provider: m.provider, tier: m.tier || "paid", name: m.name }))
      : models;
    return src.filter(m => !s || `${m.model || ""} ${m.provider || ""} ${m.name || ""}`.toLowerCase().includes(s)).slice(0, 160);
  }, [tab, catalog.models, models, q]);

  const pick = (model) => {
    onChange?.(model);
    setOpen(false);
    setQ("");
    onToast?.(`Model: ${model}`, "ok");
  };

  const addCustom = async () => {
    const id = custom.trim();
    if (!id) return;
    try { await gatewayApi.addCustomModel({ provider: "custom", model: id, tier: freeOnly ? "free" : "paid" }); } catch { /* best effort */ }
    pick(id);
    setCustom("");
  };

  const label = value || "auto";
  const pretty = label.length > 26 ? label.slice(0, 24) + "…" : label;
  const autoLabel = TEMPLATE_LABEL[label];
  const isAuto = !!autoLabel || !value || value === "auto";
  const display = isAuto
    ? (autoLabel ? t(autoLabel.ar, autoLabel.en) : t("تلقائي", "Auto"))
    : (compact ? pretty : `${t("موديل", "Model")} · ${pretty}`);

  return (
    <div className="model-wrap" ref={boxRef}>
      <button type="button" className="model-btn" onClick={() => setOpen(v => !v)} title={`Model: ${label}`}>
        <span className="conn-dot ok" style={{ width: 6, height: 6 }} />
        <span className="nm">{display}</span>
        <Icon name="chevronUp" size={12} />
      </button>

      {open && (
        <div className="model-pop" role="dialog" aria-label={t("اختر موديلًا", "Choose a model")} style={pos || undefined}>
          <div className="model-pop-head">
            <div className="model-search">
              <Icon name="search" size={14} />
              <input
                autoFocus
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder={t("ابحث عن موديل أو مزود…", "Search models or providers…")}
                onKeyDown={(e) => { if (e.key === "Enter" && tab === "catalog" && q) setCatalog(c => ({ ...c, models: [], loading: true })); }}
              />
            </div>
            <div className="model-filters">
              <button type="button" className={`chip-btn ${tab === "mine" ? "on" : ""}`} onClick={() => setTab("mine")}>{t("مزوّدي", "My providers")}</button>
              <button type="button" className={`chip-btn ${tab === "catalog" ? "on" : ""}`} onClick={() => setTab("catalog")}>{t("كل الموديلات", "All models")}</button>
              <span style={{ flex: 1 }} />
              <button type="button" className={`chip-btn ${freeOnly ? "on" : ""}`} onClick={() => setFreeOnly(v => !v)}>{t("المجاني فقط", "Free only")}</button>
            </div>
            <div className="model-filters">
              {TEMPLATES.map(([tpl, ar, en]) => (
                <button key={tpl} type="button" className={`chip-btn ${value === tpl ? "on" : ""}`} onClick={() => pick(tpl)} title={tpl}>{t(ar, en)}</button>
              ))}
            </div>
          </div>

          <div className="model-list">
            {list.map((m, idx) => (
              <button
                type="button"
                key={`${m.provider || ""}-${m.model || ""}-${idx}`}
                className={`model-row ${value === m.model ? "active" : ""}`}
                onClick={() => pick(m.model)}
              >
                <div className="mm">
                  <div className="mn">{m.model}</div>
                  <div className="mp">{m.provider || "provider"}{m.name && m.name !== m.model ? ` · ${m.name}` : ""}</div>
                </div>
                <span className={`tag ${String(m.tier).includes("free") ? "free" : "paid"}`}>{String(m.tier).includes("free") ? "Free" : "Paid"}</span>
              </button>
            ))}
            {!list.length && (
              <div className="ctx-empty">{catalog.loading ? t("جارٍ تحميل الموديلات…", "Loading models…") : t("لا توجد موديلات. أضف واحدًا أدناه.", "No models found. Add one below.")}</div>
            )}
          </div>

          <div className="model-pop-foot">
            <input
              value={custom}
              onChange={(e) => setCustom(e.target.value)}
              placeholder={t("معرّف موديل مخصص", "custom model id")}
              onKeyDown={(e) => { if (e.key === "Enter") addCustom(); }}
              dir="ltr"
            />
            <button type="button" className="btn sm" onClick={addCustom}>{t("استخدام", "Use")}</button>
          </div>
        </div>
      )}
    </div>
  );
}