/* ============================================================
   🔥😈 PORT 777 EVIL ☠️🔥👹 — Squad Panel (Hermes-style)
   تقسيم المهام على الموديلات: Planner → Workers → Aggregator
   بيسمع SSE من /api/gateway/squad/run + reconnect بـ backoff
   ============================================================ */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { gatewayApi } from './gatewayClient.js';

const TEMPLATES = [
  { id: 'auto/coding:free', label: 'auto/coding:free', hint: 'جودة كود على الـ free tiers' },
  { id: 'auto/fast:free', label: 'auto/fast:free', hint: 'أسرع موديل مجاني الأول' },
  { id: 'auto/cheap:free', label: 'auto/cheap:free', hint: 'الأرخص الأول (كله مجاني أصلاً)' },
  { id: 'auto/smart', label: 'auto/smart', hint: 'جودة الأول + استكشاف' },
  { id: 'auto/chaos', label: 'auto/chaos ⚡', hint: 'fan-out متوازي لكل الموديلات' },
];

const EXAMPLES = [
  'ابنِ لي تطبيق ويب كامل لإدارة أفكار فيديوهات يوتيوب: واجهة عربية، إضافة/حذف/بحث، حفظ محلي، تقييم بالنجوم.',
  'اعمل بوت ديسكورد يلخص المقالات العربية ويرد على قناة محددة، مع لوحة تحكم بسيطة.',
  'ابنِ داشبورد مبيعات بيقرأ CSV ويعرض Charts وتوب المنتجات بتصميم غامق.',
];

export default function SquadPanel({ onToast }) {
  const [task, setTask] = useState('');
  const [tpl, setTpl] = useState('auto/coding:free');
  const [running, setRunning] = useState(false);
  const [planner, setPlanner] = useState({ state: 'wait', model: '', pct: 0 });
  const [agg, setAgg] = useState({ state: 'wait', model: '', pct: 0 });
  const [workers, setWorkers] = useState([]); // {i,title,sub,model,provider,pct,state,output,tokens}
  const [result, setResult] = useState('');
  const [logs, setLogs] = useState([]);
  const abortRef = useRef(null);
  const retryRef = useRef({ tries: 0 });
  const termRef = useRef(null);

  const toast = (m, k) => onToast && onToast(m, k);
  const log = useCallback((msg, cls) => {
    setLogs((L) => [...L.slice(-160), { ts: new Date().toTimeString().slice(0, 8), msg, cls: cls || '' }]);
  }, []);
  useEffect(() => { termRef.current && (termRef.current.scrollTop = termRef.current.scrollHeight); }, [logs]);

  /* ---------- معالجة أحداث الـ SSE ---------- */
  const handleEvent = useCallback((ev) => {
    retryRef.current.tries = 0; // أي حدث = الاتصال سليم
    switch (ev.type) {
      case 'planner_start':
        setPlanner({ state: 'run', model: `${ev.model} @ ${ev.provider}`, pct: 12 });
        log(`Planner â†’ ${ev.model} (${ev.provider}) Â· splitting task`, 'hl'); break;
      case 'planner_done':
        setPlanner({ state: 'done', model: `${ev.model} @ ${ev.provider}`, pct: 100 });
        setWorkers(ev.subtasks.map((s, i) => ({ i, ...s, model: ev.assignments[i].model, provider: ev.assignments[i].provider, pct: 0, state: 'wait' })));
        log(`Planner done â†’ ${ev.subtasks.length} subtasks Â· X-OmniRoute-Decision: ${ev.decision}`, 'ok'); break;
      case 'worker_start':
        setWorkers((W) => W.map((w) => w.i === ev.i ? { ...w, state: 'run' } : w));
        log(`worker#${ev.i + 1} → ${ev.model} (${ev.provider}) · "${(ev.title || '').slice(0, 34)}…"`, 'hl'); break;
      case 'worker_progress':
        setWorkers((W) => W.map((w) => w.i === ev.i ? { ...w, pct: ev.pct } : w)); break;
      case 'worker_fallback':
        setWorkers((W) => W.map((w) => w.i === ev.i ? { ...w, model: ev.to.model, provider: ev.to.provider } : w));
        log(`worker#${ev.i + 1} âš  ${ev.reason} on ${ev.from} â†’ fallback â†’ ${ev.to.model}`, 'warn'); break;
      case 'worker_done':
        setWorkers((W) => W.map((w) => w.i === ev.i ? { ...w, state: 'done', pct: 100, output: ev.output, tokens: ev.tokens } : w));
        log(`worker#${ev.i + 1} âœ“ done by ${ev.model} in ${ev.secs}s`, 'ok'); break;
      case 'agg_start':
        setAgg({ state: 'run', model: `${ev.model} @ ${ev.provider}`, pct: 20 }); break;
      case 'agg_chunk':
        setResult((R) => R + ev.text);
        setAgg((A) => ({ ...A, pct: Math.min(96, A.pct + 2) })); break;
      case 'agg_done':
        setAgg({ state: 'done', model: `${ev.model} @ ${ev.provider}`, pct: 100 });
        log('â”€â”€ RUN COMPLETE Â· cost: $' + (ev.cost ?? '0.00') + ' â”€â”€', 'ok');
        toast('🏁 السرب خلّص المهمة', 'ok'); break;
      case 'error':
        log(`â›” ${ev.message}`, 'err'); toast(ev.message, 'warn'); break;
      default: break;
    }
  }, [log, toast]);

  /* ---------- التشغيل مع reconnect بـ backoff (نفس نمط الشات) ---------- */
  const start = useCallback(async () => {
    if (running) return;
    if (!task.trim()) return toast('اكتب المهمة الأول', 'warn');
    setRunning(true); setWorkers([]); setResult(''); setLogs([]);
    setPlanner({ state: 'wait', model: '', pct: 0 }); setAgg({ state: 'wait', model: '', pct: 0 });

    const attempt = () => {
      abortRef.current = gatewayApi.runSquadStream(
        { task, template: tpl },
        handleEvent,
        () => { setRunning(false); }, // [DONE]
        (err) => {
          const tries = ++retryRef.current.tries;
          if (tries <= 5) {
            const delay = Math.min(8000, 1000 * 2 ** (tries - 1)); // 1sâ†’2sâ†’4sâ†’8s
            log(`connection lost — retry ${tries}/5 after ${delay / 1000}s`, 'warn');
            setTimeout(attempt, delay);
          } else {
            setRunning(false);
            log('reconnect failed ×5 — استخدم زرار التشغيل من جديد', 'err');
            toast('الاتصال اتقطع نهائياً — جرّب تاني', 'warn');
          }
        },
      );
    };
    attempt();
  }, [running, task, tpl, handleEvent, toast, log]);

  const stop = useCallback(() => {
    abortRef.current && abortRef.current();
    setRunning(false);
    log('â–  ABORTED by user (Stop) Â· stream closed cleanly', 'err');
  }, [log]);

  useEffect(() => () => abortRef.current && abortRef.current(), []);

  return (
    <div className="gw-squad">
      <div className="gw-card">
        <div className="gw-sec-title"><span className="gw-ic">🧠</span> سرب الموديلات — أي مهمة تتقسم على الموديلات</div>
        <div className="gw-sec-sub">
          الـ <b>Planner</b> ياخد المهمة ويقسمها خطوات، كل خطوة تتوجّه لموديل مختلف حسب القالب، والـ <b>Aggregator</b> يجمّع النتيجة.
          السجل يوضح <b>مين فين عمل إيه</b> — زي logs فيديو Hermes بالظبط.
        </div>

        <div className="gw-tpl-chips">
          {TEMPLATES.map((t) => (
            <button key={t.id} type="button" title={t.hint}
              className={'gw-tpl' + (tpl === t.id ? ' gw-tpl-active' : '')}
              onClick={() => setTpl(t.id)}>{t.label}</button>
          ))}
        </div>

        <textarea className="gw-squad-input" value={task}
          onChange={(e) => setTask(e.target.value)}
          placeholder="اكتب المهمة هنا... مثال: ابنِ تطبيق ويب لإدارة أفكار فيديوهات يوتيوب" />

        <div className="gw-examples">
          {EXAMPLES.map((ex, i) => (
            <button key={i} type="button" className="gw-ex" onClick={() => setTask(ex)}>{['🎬 تطبيق أفكار يوتيوب', '🤖 بوت ديسكورد للملخصات', '📊 داشبورد مبيعات'][i]}</button>
          ))}
        </div>

        <div className="gw-run-row">
          <button className="gw-btn gw-btn-red gw-btn-run" disabled={running} onClick={start}>🚀 قسّم ونفّذ على السرب</button>
          {running && <button className="gw-btn gw-btn-stop" onClick={stop}>⏹ إيقاف</button>}
          <span className="gw-hint">التوجيه حسب القالب · fallback تلقائي لو موديل وقع</span>
        </div>
      </div>

      {(workers.length > 0 || planner.state !== 'wait') && (
        <div className="gw-pipe">
          <div className="gw-pipe-side">
            <div className="gw-stage gw-planner">
              <h5>ðŸ—ºï¸ Planner</h5>
              <div className="mono gw-stage-m">{planner.model || '—'}</div>
              <div className={'gw-st gw-st-' + planner.state}>
                {planner.state === 'run' ? 'بيقسم المهمة…' : planner.state === 'done' ? 'تمام ✅' : 'في الانتظار…'}
              </div>
              <div className="gw-pbar"><i style={{ width: planner.pct + '%' }} /></div>
            </div>
            <div className="gw-arrow">â¬‡</div>
            <div className="gw-stage gw-agg">
              <h5>ðŸ§© Aggregator</h5>
              <div className="mono gw-stage-m">{agg.model || '—'}</div>
              <div className={'gw-st gw-st-' + agg.state}>
                {agg.state === 'run' ? 'بيجمّع النتائج…' : agg.state === 'done' ? 'اتجمعت ✅' : 'في الانتظار…'}
              </div>
              <div className="gw-pbar"><i style={{ width: agg.pct + '%' }} /></div>
            </div>
          </div>
          <div className="gw-workers-col">
            <div className="gw-workers">
              {workers.map((w) => (
                <div key={w.i} className={'gw-worker gw-w-' + w.state}>
                  <div className="gw-w-t">#{w.i + 1} {w.title}</div>
                  <div className="gw-w-sub">{w.sub}</div>
                  <div className="gw-w-model mono">ðŸ¤– <b>{w.model}</b> @ {w.provider}</div>
                  <div className="gw-pbar"><i style={{ width: w.pct + '%' }} /></div>
                  {w.state === 'done' && <div className="gw-w-out">âœ“ {w.output}</div>}
                  {w.tokens && <div className="gw-w-tok">âš¡ {w.tokens}</div>}
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
        <div className="gw-term-head">
          <span>gateway@squad — سجل التوجيه</span>
          {running && <span className="gw-live"><i /> LIVE</span>}
        </div>
        <div className="gw-term-body mono" ref={termRef}>
          {logs.map((l, i) => (
            <div key={i} className={'gw-ln ' + l.cls}><span className="gw-ts">[{l.ts}]</span> {l.msg}</div>
          ))}
          {!logs.length && <div className="gw-ln">// اضغط «قسّم ونفّذ» وشوف مين بيعمل إيه 🎬</div>}
        </div>
      </div>
    </div>
  );
}
