/* Model Picker — OmniRoute-style: templates + search + free filter + ALL MODELS catalog + custom model (any provider/model). */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { gatewayApi } from './gatewayClient.js';

const TEMPLATES = ['auto', 'auto/fast:free', 'auto/cheap:free', 'auto/smart', 'auto/chaos'];

export default function ModelPicker({ value, onChange, onToast }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState('');
  const [freeOnly, setFreeOnly] = useState(true);
  const [tab, setTab] = useState('providers'); // providers | catalog
  const [models, setModels] = useState([]);
  const [catalog, setCatalog] = useState({ models: [], total: 0, loading: false });
  const [custom, setCustom] = useState('');
  const [customProvider, setCustomProvider] = useState('');
  const boxRef = useRef(null);
  const notify = (m,k) => onToast && onToast(m,k);

  useEffect(() => {
    let alive = true;
    gatewayApi.listModels(freeOnly).then((r) => {
      if (!alive) return;
      const src = Array.isArray(r.models) ? r.models : [];
      // Gateway tab/model picker: show only working/eligible models.
      setModels(src.filter((m) => m && m.provider_enabled !== false && m.model_enabled !== false && !m.cooldown));
    }).catch(() => alive && setModels([]));
    return () => { alive = false; };
  }, [freeOnly, open]);

  const loadCatalog = async (query=q) => {
    setCatalog(c => ({ ...c, loading: true }));
    try {
      const r = await gatewayApi.listCatalog(query, '', freeOnly, 300, 0);
      setCatalog({ models: r.models || [], total: r.total || 0, loading: false, providers: r.providers || [] });
    } catch (e) {
      setCatalog({ models: [], total: 0, loading: false, error: e.message });
      notify('تعذر تحميل كتالوج الموديلات: ' + e.message, 'warn');
    }
  };
  useEffect(() => { if (open && tab === 'catalog' && !catalog.models.length) loadCatalog(''); }, [open, tab]); // eslint-disable-line

  useEffect(() => {
    function onDoc(e) { if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false); }
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const filtered = useMemo(() => {
    const s = q.toLowerCase();
    const src = tab === 'catalog' ? (catalog.models || []).map(m => ({ model: m.id, provider: m.provider, tier: m.tier || 'paid', name: m.name })) : models;
    return src.filter((m) => !s || (`${m.model} ${m.provider} ${m.name||''}`).toLowerCase().includes(s)).slice(0, 120);
  }, [models, catalog.models, q, tab]);

  function pick(model) { onChange && onChange(model); setOpen(false); notify('الموديل: ' + model, 'ok'); }
  async function addCustom() {
    const id = custom.trim(); if (!id) return;
    const prov = customProvider.trim() || 'custom';
    try { await gatewayApi.addCustomModel({ provider: prov, model: id, tier: freeOnly ? 'free' : 'paid' }); } catch {}
    pick(id.includes('/') ? id : id); setCustom(''); notify('موديل مخصص: ' + id, 'ok');
  }

  return (
    <div className="gw-mpicker" ref={boxRef}>
      <button type="button" className="gw-mpick-btn" onClick={() => setOpen(!open)}>
        <span className="gw-mpick-dot" /> <span className="mono" style={{maxWidth:220,overflow:'hidden',textOverflow:'ellipsis'}}>{value || 'auto'}</span> ▾
      </button>
      {open && (
        <div className="gw-mpick-pop gw-stagger" style={{minWidth:420,maxWidth:'min(92vw,720px)'}}>
          <div className="gw-mpick-templates" style={{flexWrap:'wrap'}}>
            {TEMPLATES.map((t) => <button key={t} type="button" className={'gw-tpl' + (value===t?' gw-tpl-active':'')} onClick={() => pick(t)}>{t}</button>)}
          </div>
          <div className="gw-mpick-bar" style={{gap:8,flexWrap:'wrap'}}>
            <input autoFocus placeholder="🔍 ابحث عن موديل/مزود..." value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e)=>{ if(e.key==='Enter' && tab==='catalog') loadCatalog(q); }} />
            <button type="button" className={'gw-chip' + (freeOnly?' gw-chip-free-on':'')} onClick={() => setFreeOnly(!freeOnly)}>🆓 مجاني فقط</button>
            <button type="button" className={'gw-chip' + (tab==='providers'?' gw-chip-free-on':'')} onClick={()=>setTab('providers')}>مزودي</button>
            <button type="button" className={'gw-chip' + (tab==='catalog'?' gw-chip-free-on':'')} onClick={()=>setTab('catalog')}>جميع الموديلات</button>
            {tab==='catalog' && <button type="button" className="gw-chip" onClick={()=>loadCatalog(q)}>{catalog.loading?'...':'تحديث'}</button>}
          </div>
          {tab==='catalog' && <div className="gw-hint" style={{padding:'0 10px 6px'}}>كتالوج مستورد من OmniRoute (محلي) — {catalog.total||0} موديل. اختر أي موديل أو أضف موديل/مزود مخصصًا يدويًا.</div>}
          <div className="gw-mpick-list" style={{maxHeight:320,overflow:'auto'}}>
            {filtered.map((m,idx) => (
              <button type="button" key={`${m.provider}-${m.model}-${idx}`} className={'gw-mpick-item' + (value===m.model?' gw-current':'')} onClick={() => pick(m.model)}>
                <span className="mono gw-mpick-name" title={m.name||m.model}>{m.model}</span>
                <span className="gw-mpick-pv">{m.provider}</span>
                <span className={'gw-badge ' + (String(m.tier).includes('free')?'gw-badge-free':'gw-badge-paid')}>{String(m.tier).includes('free')?'FREE':'PAID'}</span>
              </button>
            ))}
            {!filtered.length && <div className="gw-mpick-empty">{catalog.loading?'جارٍ التحميل...':'لا نتائج — أضف موديل/مزود يدويًا بالأسفل.'}</div>}
          </div>
          <div className="gw-mpick-custom" style={{display:'grid',gridTemplateColumns:'1fr 1fr auto',gap:6}}>
            <input dir="ltr" placeholder="provider (اختياري)" value={customProvider} onChange={(e)=>setCustomProvider(e.target.value)} />
            <input dir="ltr" placeholder="model-id (أي موديل، أي مزود)" value={custom} onChange={(e)=>setCustom(e.target.value)} onKeyDown={(e)=>e.key==='Enter'&&addCustom()} />
            <button type="button" className="gw-btn gw-btn-red" onClick={addCustom}>إضافة/استخدام</button>
          </div>
        </div>
      )}
    </div>
  );
}
