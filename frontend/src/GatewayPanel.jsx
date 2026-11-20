/* Gateway Hub — features matching 00/xxxgpt_gateway_hub_demo.html, wired to real backend.
   Tabs: Gateway (providers+keys+toggles), Squad (planner/workers/aggregator SSE), Models catalog.
   Brand preserved: PORT 777 EVIL. No keys in UI; backend stores/masks. */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { gatewayApi, maskKey } from "./gatewayClient.js";

const EMPTY_FORM = { name: "", url: "", key: "", tier: "free" };
const TEMPLATES = [
  { id: "auto", label: "auto" },
  { id: "auto/fast:free", label: "auto/fast:free" },
  { id: "auto/cheap:free", label: "auto/cheap:free" },
  { id: "auto/smart", label: "auto/smart" },
  { id: "auto/chaos", label: "auto/chaos ⚡ fan-out" },
];
const EXAMPLES = [
  "ابنِ لي تطبيق ويب كامل لإدارة أفكار فيديوهات يوتيوب: واجهة عربية جميلة، إضافة/حذف/بحث أفكار، حفظ محلي، وتقييم بالنجوم — وابنِه من الصفر خطوة بخطوة.",
  "اعمل بوت ديسكورد يلخص المقالات العربية ويرد على قناة محددة، مع لوحة تحكم بسيطة.",
  "ابنِ داشبورد مبيعات بيقرأ CSV ويعرض Charts وتوب المنتجات، بخط عربي وتصميم غامق.",
];
const PREFS_KEY = "xxxgpt_ui_prefs_v1";

function readChatModel() {
  try { const p = JSON.parse(localStorage.getItem(PREFS_KEY) || "{}"); return p?.model && p.model !== "auto/coding:free" ? p.model : "auto"; } catch { return "auto"; }
}
function writeChatModel(model) {
  try { const p = JSON.parse(localStorage.getItem(PREFS_KEY) || "{}"); p.model = model; localStorage.setItem(PREFS_KEY, JSON.stringify(p)); } catch {}
}

export default function GatewayPanel({ onToast, chatModel: chatModelProp, onChatModelChange }) {
  const toast = useCallback((msg, kind) => onToast && onToast(msg, kind), [onToast]);
  const [tab, setTab] = useState("gateway"); // gateway | squad | models
  const [settings, setSettings] = useState({ activation: true, protection: true, freeOnly: true });
  const [providers, setProviders] = useState([]);
  const [summary, setSummary] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [testing, setTesting] = useState(null);
  const [saving, setSaving] = useState(false);
  const [hubModel, setHubModel] = useState(() => chatModelProp || readChatModel());
  const curModel = chatModelProp || hubModel;

  const setCurModel = useCallback((m) => {
    setHubModel(m);
    writeChatModel(m);
    onChatModelChange && onChatModelChange(m);
    toast("الآن الموديل الحالي: " + m, "ok");
  }, [onChatModelChange, toast]);

  useEffect(() => { if (chatModelProp) setHubModel(chatModelProp); }, [chatModelProp]);

  const refresh = useCallback(async (silent = false) => {
    try {
      const [s, p, sum] = await Promise.all([
        gatewayApi.getSettings(),
        gatewayApi.listProviders(),
        gatewayApi.getFreeTierSummary().catch(() => null),
      ]);
      setSettings({ activation: !!s?.activation, protection: !!s?.protection, freeOnly: !!s?.freeOnly });
      setProviders(p?.providers || []);
      if (sum) setSummary(sum);
    } catch (e) {
      if (!silent) toast("تعذر تحميل المحور: " + e.message, "warn");
    }
  }, [toast]);

  useEffect(() => { refresh(); }, [refresh]);

  async function flipSetting(k) {
    const next = { ...settings, [k]: !settings[k] };
    setSettings(next);
    const names = { activation: "التفعيل", protection: "وضع الحماية", freeOnly: "النماذج المجانية فقط" };
    try {
      await gatewayApi.setSettings({ [k]: next[k] });
      toast(names[k] + (next[k] ? ": ON ✅" : ": OFF ⛔"), next[k] ? "ok" : "warn");
      refresh(true);
    } catch (e) {
      setSettings(settings);
      toast("فشل تغيير الإعداد: " + e.message, "warn");
    }
  }

  async function addProvider(e) {
    e && e.preventDefault();
    if (!form.name || !form.url || !form.key) return toast("اكتب الاسم والـ Base URL والمفتاح", "warn");
    if (!/^https?:\/\//.test(form.url)) return toast("الـ Base URL لازم يبدأ بـ http(s)://", "warn");
    setSaving(true);
    try {
      const r = await gatewayApi.addProvider(form);
      toast(`🎉 اتوصل بـ ${form.name} — ${r.modelsCount ?? "?"} موديل اتكتشفوا`, "ok");
      setForm(EMPTY_FORM);
      refresh();
    } catch (err) { toast("فشل التوصيل: " + err.message, "warn"); }
    finally { setSaving(false); }
  }

  async function testProvider(id) {
    setTesting(id);
    try {
      const r = await gatewayApi.testProvider(id);
      if (r && r.ok === false) toast(`⛔ فشل الاتصال: ${r.error || r.name || "خطأ"}`, "warn");
      else toast(`✅ ${r.name || "المزود"} متصل — ${r.modelsCount ?? 0} موديل`, "ok");
      refresh();
    } catch (e) { toast(`⛔ فشل الاتصال: ${e.message}`, "warn"); }
    finally { setTesting(null); }
  }
  async function syncModels(id) {
    setTesting(id);
    try {
      const r = await gatewayApi.syncProviderModels(id);
      toast(`✅ تم مزامنة ${r.modelsCount || 0} موديل`, "ok");
      refresh();
    } catch (e) { toast(`فشلت مزامنة الموديلات: ${e.message}`, "warn"); }
    finally { setTesting(null); }
  }
  async function toggleProvider(p) {
    try { await gatewayApi.updateProvider(p.id, { enabled: !p.enabled }); refresh(); }
    catch (e) { toast("فشل التبديل: " + e.message, "warn"); }
  }
  async function toggleProviderFreeOnly(p) {
    try { await gatewayApi.updateProvider(p.id, { freeOnly: !p.freeOnly }); toast(`${p.name}: freeOnly ${!p.freeOnly ? "ON" : "OFF"}`, "ok"); refresh(); }
    catch (e) { toast("فشل تغيير freeOnly: " + e.message, "warn"); }
  }
  async function saveProviderBaseUrl(p, baseUrl) {
    const v = String(baseUrl || "").trim();
    if (!/^https?:\/\//.test(v)) return toast("Base URL لازم يبدأ بـ http(s)://", "warn");
    try { await gatewayApi.updateProvider(p.id, { baseUrl: v }); toast(`تم حفظ Base URL لـ ${p.name}`, "ok"); refresh(); }
    catch (e) { toast("فشل حفظ Base URL: " + e.message, "warn"); }
  }
  async function addCustomProviderModel(p, model) {
    const m = String(model || "").trim();
    if (!m) return;
    try {
      const r = await gatewayApi.addCustomModel({ provider: p.name, model: m, tier: "free", free: true, freeOnly: !!p.freeOnly });
      toast(`تمت إضافة موديل مجاني: ${m}`, "ok"); refresh(); return r;
    } catch (e) { toast("فشل إضافة الموديل: " + e.message, "warn"); }
  }
  async function deleteProvider(p) {
    if (!window.confirm(`تحذف ${p.name} ومفتاحه نهائياً؟`)) return;
    try { await gatewayApi.deleteProvider(p.id); toast("تم الحذف 🔥", "ok"); refresh(); }
    catch (e) { toast("فشل الحذف: " + e.message, "warn"); }
  }

  const enabled = providers.filter((p) => p.enabled);
  const enabledOk = providers.filter((p) => p.enabled && p.status === "ok");
  const visibleProviders = providers.filter((p) => p.enabled || p.status === "ok" || (p.modelsCount || 0) > 0);
  const freeEnabled = enabledOk.filter((p) => p.tier === "free").length;
  const keyCount = summary?.eligible_providers ?? enabled.length ?? providers.length;

  return (
    <div className="gw-hub">
      <header className="gw-hub-header">
        <div className="gw-hub-logo">
          <div className="gw-hub-mark">⬢</div>
          <div>🔥😈 PORT 777 EVIL ☠️🔥👹 <em>Gateway Hub</em><small>OmniRoute Edition · مزودين + مفاتيح + سرب + كتالوج</small></div>
        </div>
        <div className="gw-statusbar">
          <button type="button" className={"gw-chip " + (settings.activation ? "on" : "")} onClick={() => flipSetting("activation")} title="التفعيل: لو مقفول، الطلبات fail-closed للمسار الآمن/المحلي حسب backend"><span className="gw-dot" />التفعيل <b>{settings.activation ? "ON" : "OFF"}</b></button>
          <button type="button" className={"gw-chip " + (settings.protection ? "on" : "")} onClick={() => flipSetting("protection")} title="وضع الحماية: guard/fail-closed حسب إعدادات gateway"><span className="gw-dot" />🛡️ الحماية <b>{settings.protection ? "ON" : "OFF"}</b></button>
          <button type="button" className={"gw-chip gw-chip-free " + (settings.freeOnly ? "on" : "")} onClick={() => flipSetting("freeOnly")} title="النماذج المجانية فقط"><span className="gw-dot" />مجاني فقط <b>{settings.freeOnly ? "ON" : "OFF"}</b></button>
          <span className="gw-chip" title="مزودين/مفاتيح مهيأة"><span className="gw-dot" style={{background:"var(--red2,#ef4444)"}} />🔑 <b>{keyCount}</b> مزود</span>
          <span className="gw-chip" title="الموديل/المسار الحالي للشات"><span className="gw-dot" style={{background:"var(--red2,#ef4444)"}} /><b className="mono" style={{fontSize:".72rem",maxWidth:180,overflow:"hidden",textOverflow:"ellipsis"}}>{curModel}</b></span>
        </div>
      </header>

      <div className="gw-tabs" role="tablist">
        <button type="button" role="tab" aria-selected={tab==="gateway"} className={"gw-tab" + (tab==="gateway"?" active":"")} onClick={()=>setTab("gateway")}>🛰️ المحور — المزودين والمفاتيح</button>
        <button type="button" role="tab" aria-selected={tab==="squad"} className={"gw-tab" + (tab==="squad"?" active":"")} onClick={()=>setTab("squad")}>🧠 سرب الموديلات — تقسيم المهام</button>
        <button type="button" role="tab" aria-selected={tab==="models"} className={"gw-tab" + (tab==="models"?" active":"")} onClick={()=>setTab("models")}>📚 كتالوج النماذج</button>
        <button type="button" role="tab" aria-selected={tab==="compare"} className={"gw-tab" + (tab==="compare"?" active":"")} onClick={()=>setTab("compare")}>⚖️ مقارنة النماذج</button>
      </div>

      {tab === "gateway" && (
        <GatewayTab settings={settings} flipSetting={flipSetting} form={form} setForm={setForm} addProvider={addProvider} saving={saving}
          providers={providers} visibleProviders={visibleProviders} enabledOk={enabledOk} freeEnabled={freeEnabled}
          testing={testing} testProvider={testProvider} syncModels={syncModels} toggleProvider={toggleProvider} toggleProviderFreeOnly={toggleProviderFreeOnly} saveProviderBaseUrl={saveProviderBaseUrl} addCustomProviderModel={addCustomProviderModel} deleteProvider={deleteProvider} />
      )}
      {tab === "squad" && <SquadTab toast={toast} settings={settings} curModel={curModel} />}
      {tab === "models" && <ModelsTab settings={settings} toast={toast} curModel={curModel} setCurModel={setCurModel} />}
      {tab === "compare" && <CompareTab toast={toast} settings={settings} />}
    </div>
  );
}

function ToggleCard({ on, onFlip, icon, title, badge, desc, onText, offText, free }) {
  return (
    <div className={"gw-card gw-toggle " + (on ? "gw-on" : "")}>
      <h4>{icon} {title} <span className={"gw-badge " + (on ? "gw-badge-ok" : "")} style={{marginInlineStart:"auto"}}>{badge}</span></h4>
      <p>{desc}</p>
      <div className="gw-switch-row">
        <button type="button" className={"gw-sw " + (free ? "gw-sw-free " : "") + (on ? "gw-sw-on" : "")} onClick={onFlip} aria-label={title} />
        <span className="gw-sw-txt">{on ? onText : offText}</span>
      </div>
    </div>
  );
}

function GatewayTab({ settings, flipSetting, form, setForm, addProvider, saving, providers, visibleProviders, enabledOk, freeEnabled, testing, testProvider, syncModels, toggleProvider, toggleProviderFreeOnly, saveProviderBaseUrl, addCustomProviderModel, deleteProvider }) {
  return (
    <div className="gw-wrap">
      <div className="gw-toggles gw-stagger">
        <ToggleCard on={settings.activation} onFlip={() => flipSetting("activation")} icon="⚡" title="تفعيل المحور" badge={settings.activation ? "Active" : "Closed"}
          desc="المفتاح الرئيسي. لما يكون ON، الشات/المهام تمر على مزودينك حسب إعدادات gateway. لما يكون OFF، الطلبات الخارجية/المغيرة تُمنع fail-closed حسب backend."
          onText="مُفعّل — التوجيه عبر مزودينك شغال" offText="متقفل — fail-closed" />
        <ToggleCard on={settings.protection} onFlip={() => flipSetting("protection")} icon="🛡️" title="وضع الحماية" badge={settings.protection ? "Guarded" : "Off"}
          desc="حماية/حراسة على مسارات gateway (وتطبيق fail-closed عند الانتهاك حسب backend). المفاتيح لا تُعرض كاملة في الواجهة."
          onText="الحماية شغالة" offText="⚠️ الحماية مقفولة" />
        <ToggleCard free on={settings.freeOnly} onFlip={() => flipSetting("freeOnly")} icon="🆓" title="النماذج المجانية فقط" badge={settings.freeOnly ? "FREE" : "ALL"}
          desc="يقفل/يستبعد الموديلات المدفوعة من الاختيار والتوجيه ويقصر المسار على free tiers المزودين المفعّلين."
          onText="مجاني فقط — المدفوع مقفول" offText="كل الموديلات مسموحة (مجاني + مدفوع)" />
      </div>

      <form className="gw-card" onSubmit={addProvider}>
        <div className="gw-sec-title"><span className="gw-ic">➕</span> إضافة موديل جديد — أي موديل، أي مزوّد</div>
        <div className="gw-sec-sub">OpenAI-compatible endpoint: ضع الـ Base URL + API key، والمحور يحاول اكتشاف الموديلات من <code>GET {'{base}'}/v1/models</code>. المفتاح يُخزن في backend ويظهر متقنع.</div>
        <div className="gw-addform">
          <label className="gw-field"><span>اسم المزوّد</span><input value={form.name} onChange={(e)=>setForm({...form,name:e.target.value})} placeholder="Groq / OpenRouter / NVIDIA / سيرفري" /></label>
          <label className="gw-field"><span>Base URL</span><input dir="ltr" value={form.url} onChange={(e)=>setForm({...form,url:e.target.value})} placeholder="https://api.groq.com/openai/v1" /></label>
          <label className="gw-field"><span>API Key</span><input dir="ltr" type="password" value={form.key} onChange={(e)=>setForm({...form,key:e.target.value})} placeholder="gsk_... / sk-..." autoComplete="off" /></label>
          <label className="gw-field"><span>النوع</span><select value={form.tier} onChange={(e)=>setForm({...form,tier:e.target.value})}><option value="free">🆓 مجاني (free tier)</option><option value="paid">💰 مدفوع</option></select></label>
          <button className="gw-btn gw-btn-red" disabled={saving} type="submit">{saving ? "جارٍ التوصيل…" : "توصيل المزوّد"}</button>
        </div>
        <div className="gw-hint">🔒 المفتاح في الـ backend فقط ويظهر متقنع (<code>{maskKey("gsk_demo7f2a9b1c")}</code>).</div>
      </form>

      <div className="gw-sec-title" style={{marginTop:4}}><span className="gw-ic">🔗</span> المزودين المتصلين <span className="gw-badge gw-badge-free">{freeEnabled} مجاني يعمل</span><span className="gw-badge">{enabledOk.length} يعمل</span><span className="gw-badge">/ {providers.length} مزود</span></div>
      <div className="gw-grid gw-stagger">
        {visibleProviders.map((p) => (
          <ProviderCard key={p.id} p={p} testing={testing} testProvider={testProvider} syncModels={syncModels}
            toggleProvider={toggleProvider} toggleProviderFreeOnly={toggleProviderFreeOnly}
            saveProviderBaseUrl={saveProviderBaseUrl} addCustomProviderModel={addCustomProviderModel}
            deleteProvider={deleteProvider} />
        ))}
        {!visibleProviders.length && <div className="gw-card gw-empty">مفيش مزودين — أضف مزود OpenAI-compatible أو فعّل/اختبر مزود موجود.</div>}
      </div>
    </div>
  );
}



function ProviderCard({ p, testing, testProvider, syncModels, toggleProvider, toggleProviderFreeOnly, saveProviderBaseUrl, addCustomProviderModel, deleteProvider }) {
  const [editUrl, setEditUrl] = React.useState(false);
  const [baseUrl, setBaseUrl] = React.useState(p.baseUrl || "");
  const [customModel, setCustomModel] = React.useState("");
  React.useEffect(() => { setBaseUrl(p.baseUrl || ""); }, [p.baseUrl, p.id]);
  const working = p.enabled && p.status === "ok";
  const shown = p.modelsCount ?? (p.models || []).length;
  const all = p.allModelsCount ?? shown;
  return (
    <div className={"gw-prov" + (p.enabled ? "" : " gw-off")}>
      <div className="gw-prov-head">
        <div className="gw-avatar">{String(p.name || "??").slice(0, 2).toUpperCase()}</div>
        <div className="gw-prov-id" style={{minWidth:0,flex:1}}>
          <div className="gw-nm">{p.name}</div>
          {!editUrl ? <div className="gw-url mono" title={p.baseUrl} style={{overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{p.baseUrl || "(no base URL)"}</div>
            : <div className="row" style={{gap:6,marginTop:4}}><input dir="ltr" className="gw-inp mono" value={baseUrl} onChange={(e)=>setBaseUrl(e.target.value)} placeholder="https://.../v1" style={{flex:1,minWidth:120}} /><button type="button" className="gw-btn gw-btn-ghost" onClick={()=>{saveProviderBaseUrl(p,baseUrl); setEditUrl(false);}}>حفظ</button><button type="button" className="gw-btn gw-btn-ghost" onClick={()=>{setBaseUrl(p.baseUrl||""); setEditUrl(false);}}>إلغاء</button></div>}
        </div>
        <span className={"gw-badge " + (working ? "gw-badge-ok" : p.enabled ? "gw-badge-err" : "")}>{working ? "متصل" : p.enabled ? String(p.status || "غير متصل") : "معطل"}</span>
      </div>
      <div className="gw-key mono">🔑 {maskKey(p.keyMasked || p.key)}</div>
      <div className="gw-meta" style={{flexWrap:"wrap",gap:6}}>
        <span>📦 <b>{shown}</b>{all !== shown ? <span className="muted">/{all}</span> : null} موديل</span>
        <span className={"gw-badge " + (p.tier === "free" ? "gw-badge-free" : "gw-badge-paid")}>{p.tier === "free" ? "🆓 Free tier" : "💰 Paid"}</span>
        <button type="button" className={"gw-badge " + (p.freeOnly ? "gw-badge-free" : "")} onClick={()=>toggleProviderFreeOnly(p)} title="تبديل freeOnly لهذا المزود (يؤثر على النماذج المعروضة/المسار)">freeOnly: {p.freeOnly ? "ON" : "OFF"}</button>
        {!working && p.enabled ? <span className="gw-badge gw-badge-err">غير جاهز للتوجيه</span> : null}
        {shown === 0 ? <span className="gw-badge gw-badge-warn">أضف Base URL متوافق OpenAI أو أضف موديل يدوي</span> : null}
      </div>
      <div className="row" style={{gap:6,marginTop:6,flexWrap:"wrap"}}>
        <input dir="ltr" className="gw-inp mono" value={customModel} onChange={(e)=>setCustomModel(e.target.value)} placeholder="إضافة موديل يدوي (مثال: model-id:free)" style={{flex:1,minWidth:150}} />
        <button type="button" className="gw-btn gw-btn-ghost" onClick={async()=>{ await addCustomProviderModel(p, customModel); setCustomModel(""); }}>+ موديل مجاني</button>
      </div>
      <div className="gw-acts" style={{flexWrap:"wrap"}}>
        <button type="button" className="gw-btn gw-btn-ghost" disabled={testing === p.id} onClick={() => testProvider(p.id)}>{testing === p.id ? <span className="gw-spin" /> : "🔌"} اختبار</button>
        <button type="button" className="gw-btn gw-btn-ghost" disabled={testing === p.id} onClick={() => syncModels(p.id)} title="جلب الموديلات من المزود">{testing === p.id ? <span className="gw-spin" /> : "📦"} مزامنة</button>
        <button type="button" className="gw-btn gw-btn-ghost" onClick={() => setEditUrl(v=>!v)}>✎ Base URL</button>
        <button type="button" className="gw-btn gw-btn-ghost" onClick={() => toggleProvider(p)}>{p.enabled ? "⏸ تعطيل" : "▶ تفعيل"}</button>
        <button type="button" className="gw-btn gw-btn-danger" onClick={() => deleteProvider(p)}>🗑</button>
      </div>
    </div>
  );
}

function SquadTab({ toast, settings, curModel }) {
  const [task, setTask] = useState("");
  const [tpl, setTpl] = useState(curModel && curModel !== "auto" && TEMPLATES.some(t=>t.id===curModel) ? curModel : "auto");
  const [running, setRunning] = useState(false);
  const [planner, setPlanner] = useState({ state: "wait", model: "", pct: 0 });
  const [agg, setAgg] = useState({ state: "wait", model: "", pct: 0 });
  const [workers, setWorkers] = useState([]);
  const [result, setResult] = useState("");
  const [logs, setLogs] = useState([]);
  const abortRef = useRef(null);
  const retryRef = useRef({ tries: 0 });
  const termRef = useRef(null);
  const log = useCallback((msg, cls) => setLogs((L) => [...L.slice(-180), { ts: new Date().toTimeString().slice(0, 8), msg, cls: cls || "" }]), []);
  useEffect(() => { termRef.current && (termRef.current.scrollTop = termRef.current.scrollHeight); }, [logs]);
  useEffect(() => () => abortRef.current && abortRef.current(), []);

  const handleEvent = useCallback((ev) => {
    retryRef.current.tries = 0;
    switch (ev.type) {
      case "planner_start":
        setPlanner({ state: "run", model: `${ev.model} @ ${ev.provider}`, pct: 12 });
        log(`Planner → ${ev.model} (${ev.provider}) · splitting task`, "hl"); break;
      case "planner_done":
        setPlanner({ state: "done", model: `${ev.model} @ ${ev.provider}`, pct: 100 });
        setWorkers((ev.subtasks || []).map((s, i) => ({ i, ...s, model: ev.assignments?.[i]?.model || "?", provider: ev.assignments?.[i]?.provider || "?", pct: 0, state: "wait" })));
        log(`Planner done → ${(ev.subtasks || []).length} subtasks · decision: ${ev.decision || tpl}`, "ok"); break;
      case "worker_start":
        setWorkers((W) => W.map((w) => w.i === ev.i ? { ...w, state: "run" } : w));
        log(`worker#${(ev.i ?? 0) + 1} → ${ev.model} (${ev.provider}) · "${(ev.title || "").slice(0, 34)}…"`, "hl"); break;
      case "worker_progress":
        setWorkers((W) => W.map((w) => w.i === ev.i ? { ...w, pct: ev.pct } : w)); break;
      case "worker_fallback":
        setWorkers((W) => W.map((w) => w.i === ev.i ? { ...w, model: ev.to?.model || w.model, provider: ev.to?.provider || w.provider } : w));
        log(`worker#${(ev.i ?? 0) + 1} ⚠ ${ev.reason || "quota/provider"} on ${ev.from} → fallback → ${ev.to?.model}`, "warn"); break;
      case "worker_done":
        setWorkers((W) => W.map((w) => w.i === ev.i ? { ...w, state: "done", pct: 100, output: ev.output, tokens: ev.tokens } : w));
        log(`worker#${(ev.i ?? 0) + 1} ✓ done by ${ev.model} in ${ev.secs ?? "?"}s`, "ok"); break;
      case "agg_start":
        setAgg({ state: "run", model: `${ev.model} @ ${ev.provider}`, pct: 20 }); break;
      case "agg_chunk":
        setResult((R) => R + (ev.text || ""));
        setAgg((A) => ({ ...A, pct: Math.min(96, (A.pct || 20) + 2) })); break;
      case "agg_done":
        setAgg({ state: "done", model: `${ev.model} @ ${ev.provider}`, pct: 100 });
        log(`── RUN COMPLETE · cost: $${ev.cost ?? "0.00"} ──`, "ok");
        toast("🏁 السرب خلّص المهمة", "ok"); break;
      case "error":
        log(`⛔ ${ev.message}`, "err"); toast(ev.message || "خطأ", "warn"); break;
      default: break;
    }
  }, [log, toast, tpl]);

  const start = useCallback(() => {
    if (running) return;
    if (!task.trim()) return toast("اكتب المهمة الأول", "warn");
    if (!settings.activation) { log("REQUEST blocked · activation=OFF · fail-closed", "err"); return toast("⛔ المحور متقفل (fail-closed) — فعّل التفعيل الأول", "warn"); }
    setRunning(true); setWorkers([]); setResult(""); setLogs([]);
    setPlanner({ state: "wait", model: "", pct: 0 }); setAgg({ state: "wait", model: "", pct: 0 });
    log(`POST /api/gateway/squad/run · template=${tpl}`, "hl");
    if (settings.protection) log("🛡️ protection=ON (gateway guard)", "warn");
    const attempt = () => {
      abortRef.current = gatewayApi.runSquadStream(
        { task, template: tpl },
        handleEvent,
        () => { setRunning(false); },
        (err) => {
          const tries = ++retryRef.current.tries;
          if (tries <= 5) {
            const delay = Math.min(8000, 1000 * 2 ** (tries - 1));
            log(`connection lost — retry ${tries}/5 after ${delay / 1000}s`, "warn");
            setTimeout(attempt, delay);
          } else {
            setRunning(false);
            log("reconnect failed ×5 — جرّب التشغيل من جديد", "err");
            toast("الاتصال اتقطع نهائياً — جرّب تاني", "warn");
          }
        },
      );
    };
    attempt();
  }, [running, task, tpl, settings, handleEvent, toast, log]);

  const stop = useCallback(() => {
    abortRef.current && abortRef.current();
    setRunning(false);
    log("■ ABORTED by user (Stop) · stream closed cleanly", "err");
  }, [log]);

  return (
    <div className="gw-squad">
      <div className="gw-card">
        <div className="gw-sec-title"><span className="gw-ic">🧠</span> سرب الموديلات — أي مهمة تتقسم على الموديلات</div>
        <div className="gw-sec-sub">الـ <b>Planner</b> يقسم المهمة خطوات، كل خطوة تتوجّه لموديل مختلف حسب القالب، والـ <b>Aggregator</b> يجمّع النتيجة. السجل يوضح مين فين عمل إيه (SSE من backend).</div>
        <div className="gw-tpl-chips">
          {TEMPLATES.map((t) => (
            <button key={t.id} type="button" className={"gw-tpl" + (tpl === t.id ? " gw-tpl-active" : "")} onClick={() => setTpl(t.id)}>{t.label}</button>
          ))}
        </div>
        <textarea className="gw-squad-input" value={task} onChange={(e) => setTask(e.target.value)} placeholder="اكتب المهمة هنا... مثال: ابنِ تطبيق ويب لإدارة أفكار فيديوهات يوتيوب" />
        <div className="gw-examples">
          {["🎬 تطبيق أفكار يوتيوب", "🤖 بوت ديسكورد للملخصات", "📊 داشبورد مبيعات"].map((label, i) => (
            <button key={i} type="button" className="gw-ex" onClick={() => setTask(EXAMPLES[i])}>{label}</button>
          ))}
        </div>
        <div className="gw-run-row">
          <button className="gw-btn gw-btn-red gw-btn-run" disabled={running} onClick={start}>🚀 قسّم ونفّذ على السرب</button>
          {running && <button className="gw-btn gw-btn-stop" onClick={stop}>⏹ إيقاف</button>}
          <span className="gw-hint">التوجيه حسب القالب · fallback تلقائي لو موديل وقع · activation/fail-closed يحترم إعدادات gateway</span>
        </div>
      </div>

      {(workers.length > 0 || planner.state !== "wait") && (
        <div className="gw-pipe">
          <div className="gw-pipe-side">
            <div className="gw-stage gw-planner">
              <h5>🗺️ Planner</h5>
              <div className="mono gw-stage-m">{planner.model || "—"}</div>
              <div className={"gw-st gw-st-" + planner.state}>{planner.state === "run" ? "بيقسم المهمة…" : planner.state === "done" ? "تمام ✅" : "في الانتظار…"}</div>
              <div className="gw-pbar"><i style={{ width: planner.pct + "%" }} /></div>
            </div>
            <div className="gw-arrow">⬇</div>
            <div className="gw-stage gw-agg">
              <h5>🧩 Aggregator</h5>
              <div className="mono gw-stage-m">{agg.model || "—"}</div>
              <div className={"gw-st gw-st-" + agg.state}>{agg.state === "run" ? "بيجمّع النتائج…" : agg.state === "done" ? "اتجمعت ✅" : "في الانتظار…"}</div>
              <div className="gw-pbar"><i style={{ width: agg.pct + "%" }} /></div>
            </div>
          </div>
          <div className="gw-workers-col">
            <div className="gw-sec-title" style={{marginBottom:10,fontSize:".9rem"}}><span className="gw-ic">⚙️</span> خط الشغل — <span style={{color:"var(--red2,#ef4444)"}}>{workers.length}</span> خطوة على <span style={{color:"var(--red2,#ef4444)"}}>{new Set(workers.map(w=>w.model).filter(Boolean)).size}</span> موديل</div>
            <div className="gw-workers">
              {workers.map((w) => (
                <div key={w.i} className={"gw-worker gw-w-" + w.state}>
                  <div className="gw-w-t">#{w.i + 1} {w.title}</div>
                  <div className="gw-w-sub">{w.sub}</div>
                  <div className="gw-w-model mono">🤖 <b>{w.model}</b> @ {w.provider}</div>
                  <div className="gw-pbar"><i style={{ width: w.pct + "%" }} /></div>
                  {w.state === "done" && <div className="gw-w-out">✓ {w.output}</div>}
                  {w.tokens ? <div className="gw-w-tok">⚡ {w.tokens} tokens</div> : null}
                </div>
              ))}
            </div>
            {result && (
              <div className="gw-result">
                <h4>🧩 النتيجة النهائية المجمّعة</h4>
                <div className="gw-result-txt">{result}</div>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="gw-term">
        <div className="gw-term-head"><span>gateway@squad — سجل التوجيه</span>{running && <span className="gw-live"><i /> LIVE</span>}</div>
        <div className="gw-term-body mono" ref={termRef}>
          {logs.map((l, i) => (<div key={i} className={"gw-ln " + l.cls}><span className="gw-ts">[{l.ts}]</span> {l.msg}</div>))}
          {!logs.length && <div className="gw-ln">// اضغط «قسّم ونفّذ» وشوف مين بيعمل إيه 🎬</div>}
        </div>
      </div>
    </div>
  );
}


function CompareTab({ toast, settings }) {
  const [prompt, setPrompt] = React.useState("");
  const [modelsText, setModelsText] = React.useState("");
  const [running, setRunning] = React.useState(false);
  const [result, setResult] = React.useState(null);
  const [catalog, setCatalog] = React.useState([]);
  const [selected, setSelected] = React.useState([]);

  React.useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const r = await gatewayApi.listCatalog("", "", !!settings?.freeOnly, 120, 0);
        if (alive) setCatalog(Array.isArray(r?.models) ? r.models : []);
      } catch {}
    })();
    return () => { alive = false; };
  }, [settings?.freeOnly]);

  const toggleModel = (id) => {
    setSelected((s) => s.includes(id) ? s.filter(x => x !== id) : (s.length >= 6 ? s : [...s, id]));
  };

  const run = async () => {
    const p = String(prompt || "").trim();
    if (!p) return toast("اكتب prompt للمقارنة", "warn");
    const manual = String(modelsText || "").split(/\n|,/).map(x => x.trim()).filter(Boolean);
    const models = Array.from(new Set([...selected, ...manual])).slice(0, 6);
    setRunning(true); setResult(null);
    try {
      const r = await gatewayApi.compareModels({ prompt: p, models, max_tokens: 700, temperature: 0.2 });
      setResult(r);
      toast(`تمت المقارنة: ${r?.ok_count || 0}/${r?.count || 0}`, (r?.ok_count ? "ok" : "warn"));
    } catch (e) {
      toast("فشلت المقارنة: " + (e?.message || e), "warn");
      setResult({ error: e?.message || String(e), results: [] });
    } finally { setRunning(false); }
  };

  return (
    <div className="gw-wrap" style={{ display: "grid", gap: 12 }}>
      <div className="gw-card" style={{ padding: 12, display: "grid", gap: 10 }}>
        <div className="gw-sec-title"><span className="gw-ic">⚖️</span> مقارنة نماذج (Parallel Compare)</div>
        <div className="gw-sec-sub">يرسل نفس الـ prompt لأكثر من موديل من مزودين gateway المتصلين ويعرض النتائج جنبًا إلى جنب. اترك الاختيار فارغًا لاستخدام أول موديلات متاحة تلقائيًا.</div>
        <textarea className="gw-inp" rows={5} value={prompt} onChange={e=>setPrompt(e.target.value)} placeholder="اكتب المهمة/السؤال للمقارنة..." />
        <div style={{ display: "grid", gap: 6 }}>
          <div className="muted" style={{ fontSize: 12 }}>موديلات يدوية (اختياري): <code>providerId::modelId</code> أو <code>modelId</code> (سطر/فاصلة)</div>
          <textarea className="gw-inp mono" rows={3} dir="ltr" value={modelsText} onChange={e=>setModelsText(e.target.value)} placeholder={"providerId::model-id\nopenai/gpt-4o-mini"} />
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <button type="button" className="gw-btn gw-btn-red" onClick={run} disabled={running}>{running ? "جارٍ المقارنة…" : "تشغيل المقارنة"}</button>
          <button type="button" className="gw-btn gw-btn-ghost" onClick={()=>{setSelected([]); setModelsText(""); setResult(null);}}>مسح</button>
          <span className="gw-badge">مختار: {selected.length}/6</span>
        </div>
      </div>

      {!!catalog.length && (
        <div className="gw-card" style={{ padding: 12 }}>
          <div className="gw-sec-title" style={{ marginBottom: 8 }}>اختيار سريع من الكتالوج</div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", maxHeight: 220, overflow: "auto" }}>
            {catalog.slice(0, 120).map((m, i) => {
              const id = m?.id || m?.model || m?.name;
              if (!id) return null;
              const on = selected.includes(id);
              return <button key={`${id}-${i}`} type="button" className={"gw-chip " + (on ? "on" : "")} onClick={()=>toggleModel(id)} title={id}><span className="mono" style={{ fontSize: 11 }}>{String(id).slice(0, 42)}</span></button>;
            })}
          </div>
        </div>
      )}

      {result && (
        <div className="gw-card" style={{ padding: 12, display: "grid", gap: 10 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <div className="gw-sec-title" style={{ margin: 0 }}><span className="gw-ic">📊</span> النتائج</div>
            <span className="gw-badge gw-badge-ok">OK: {result.ok_count || 0}</span>
            <span className="gw-badge">Total: {result.count || 0}</span>
            {result.primary ? <span className="gw-badge gw-badge-free">Primary: {String(result.primary.model || "").slice(0, 40)}</span> : null}
            {result.error ? <span className="gw-badge gw-badge-err">{String(result.error).slice(0, 120)}</span> : null}
          </div>
          <div style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
            {(result.results || []).map((r, idx) => (
              <div key={idx} className="gw-prov" style={{ margin: 0 }}>
                <div className="gw-prov-head">
                  <div className="gw-avatar">{String(r.provider || "?").slice(0,2).toUpperCase()}</div>
                  <div className="gw-prov-id" style={{ minWidth: 0 }}>
                    <div className="gw-nm" style={{ fontSize: 13 }}>{r.provider || "provider"}</div>
                    <div className="gw-url mono" style={{ fontSize: 11, overflow: "hidden", textOverflow: "ellipsis" }}>{r.model}</div>
                  </div>
                  <span className={"gw-badge " + (r.ok ? "gw-badge-ok" : "gw-badge-err")}>{r.ok ? "OK" : "ERR"}</span>
                </div>
                <div className="gw-meta" style={{ gap: 6, flexWrap: "wrap" }}>
                  <span>⏱ {r.ms ?? "?"} ms</span>
                  {r.status ? <span>HTTP {r.status}</span> : null}
                  {r.usage && (r.usage.total_tokens || r.usage.prompt_tokens) ? <span>tokens: {r.usage.total_tokens ?? "?"}</span> : null}
                </div>
                {r.error ? <div className="gw-card" style={{ background: "rgba(239,68,68,.08)", color: "#fca5a5", padding: 8, fontSize: 12, whiteSpace: "pre-wrap" }}>{String(r.error)}</div> : null}
                <pre style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: 12, maxHeight: 360, overflow: "auto", padding: 10, borderRadius: 10, background: "rgba(0,0,0,.25)", border: "1px solid rgba(255,255,255,.06)" }}>{String(r.content || r.error || "(no content)")}</pre>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ModelsTab({ settings, toast, curModel, setCurModel }) {
  const [q, setQ] = useState("");
  const [catalog, setCatalog] = useState({ models: [], total: 0, loading: true, providers: [] });
  const [freeOnly, setFreeOnly] = useState(!!settings.freeOnly);
  const [custom, setCustom] = useState("");
  const [customProvider, setCustomProvider] = useState("");

  const load = useCallback(async (query = q, free = freeOnly) => {
    setCatalog((c) => ({ ...c, loading: true }));
    try {
      const r = await gatewayApi.listCatalog(query, "", free, 500, 0);
      setCatalog({ models: r.models || [], total: r.total || 0, loading: false, providers: r.providers || [] });
    } catch (e) {
      setCatalog({ models: [], total: 0, loading: false, providers: [], error: e.message });
    }
  }, [q, freeOnly]);

  useEffect(() => { load("", freeOnly); }, [freeOnly]); // eslint-disable-line

  const groups = useMemo(() => {
    const out = {};
    (catalog.models || []).forEach((m) => {
      const pv = m.provider || "custom";
      (out[pv] = out[pv] || []).push(m);
    });
    return out;
  }, [catalog.models]);

  async function addCustom() {
    const id = custom.trim(); if (!id) return;
    const prov = customProvider.trim() || "custom";
    try { await gatewayApi.addCustomModel({ provider: prov, model: id, tier: freeOnly ? "free" : "paid" }); } catch {}
    setCurModel(id.includes("/") ? id : id);
    setCustom("");
    toast("موديل مخصص: " + id, "ok");
  }

  return (
    <div className="gw-wrap">
      <div className="gw-models-bar">
        <input value={q} onChange={(e)=>setQ(e.target.value)} onKeyDown={(e)=>e.key==="Enter"&&load(q,freeOnly)} placeholder="🔍 ابحث عن موديل... (llama, deepseek, gpt, gemini)" />
        <button type="button" className={"gw-chip gw-chip-free " + (freeOnly ? "on" : "")} onClick={()=>setFreeOnly(v=>!v)}><span className="gw-dot" />مجاني فقط</button>
        <button type="button" className="gw-chip" onClick={()=>load(q,freeOnly)}>{catalog.loading ? "..." : "تحديث"}</button>
        <span className="gw-chip" style={{cursor:"default"}}><span className="gw-dot" style={{background:"var(--red2,#ef4444)"}} /><b>{catalog.total || 0}</b> موديل</span>
      </div>
      <div className="gw-hint">كتالوج OmniRoute محلي (قراءة فقط) + مزامنة مزودين من /v1/models + إضافة موديل مخصص يدويًا. اختيار موديل هنا يحدّث موديل الشات المحفوظ (عبر App/local prefs).</div>
      <div className="gw-card" style={{padding:12}}>
        <div className="gw-mpick-custom" style={{marginTop:0}}>
          <input dir="ltr" placeholder="provider (اختياري)" value={customProvider} onChange={(e)=>setCustomProvider(e.target.value)} />
          <input dir="ltr" placeholder="model-id (أي موديل، أي مزود)" value={custom} onChange={(e)=>setCustom(e.target.value)} onKeyDown={(e)=>e.key==="Enter"&&addCustom()} />
          <button type="button" className="gw-btn gw-btn-red" onClick={addCustom}>إضافة/استخدام</button>
        </div>
      </div>
      {catalog.error && <div className="gw-card gw-empty">تعذر تحميل الكتالوج: {catalog.error}</div>}
      {!catalog.loading && !Object.keys(groups).length && !catalog.error && <div className="gw-card gw-empty">مفيش موديلات مطابقة — جرّب بحث آخر أو اقفل «مجاني فقط» أو زوّد مزود/موديل.</div>}
      {Object.keys(groups).map((pv) => (
        <div key={pv} className="gw-pgroup">
          <h4>▸ {pv} <b>{groups[pv].length}</b> موديل</h4>
          <div className="gw-models-grid">
            {groups[pv].slice(0, 120).map((m, idx) => {
              const id = m.id || m.model || m.name;
              const isFree = String(m.tier || "").includes("free") || String(id).includes(":free");
              return (
                <button type="button" key={`${pv}-${id}-${idx}`} className={"gw-model-card" + (curModel === id ? " current" : "")} onClick={() => setCurModel(id)}>
                  <div className="gw-model-nm mono">{id}</div>
                  <div className="gw-model-pv">{pv}</div>
                  <div className="gw-model-row">
                    <span className={"gw-badge " + (isFree ? "gw-badge-free" : "gw-badge-paid")}>{isFree ? "🆓 FREE" : "💰 PAID"}</span>
                    <span className="gw-use">استخدمه ←</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
