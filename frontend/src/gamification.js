// Gamification client — talks to /api/gamification/* and falls back to
// localStorage when the backend is unreachable, so XP is never lost.
const ROOT = "/api/gamification";
const LS_KEY = "xxxgpt_gamification_v1";

const FALLBACK_CATALOG = {
  levels: [
    { level: 1, name: "Trainee", xp_required: 0 },
    { level: 2, name: "Analyst I", xp_required: 500 },
    { level: 3, name: "Analyst II", xp_required: 1500 },
    { level: 4, name: "Senior", xp_required: 3500 },
    { level: 5, name: "Expert", xp_required: 7500 },
    { level: 6, name: "Elite", xp_required: 15000 },
    { level: 7, name: "Legendary", xp_required: 30000 },
  ],
  events: {
    analysis_complete: { xp: 50, metric: "analyses" },
    ioc_extracted: { xp: 5, metric: "iocs" },
    yara_generated: { xp: 30, metric: "yara" },
    sigma_generated: { xp: 30, metric: "sigma" },
    hunt_completed: { xp: 100, metric: "hunts" },
    report_generated: { xp: 75, metric: "reports" },
    attribution_correct: { xp: 200, metric: "attributions" },
    sandbox_run: { xp: 15, metric: "sandbox_runs" },
    intel_lookup: { xp: 5, metric: "intel_lookups" },
    re_session: { xp: 20, metric: "re_sessions" },
    detection_deployed: { xp: 40, metric: "detections" },
  },
  achievements: [],
};

let _catalog = null;

async function jfetch(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  const tok = localStorage.getItem("🔥😈 PORT 777 EVIL ☠️🔥👹_token");
  if (tok) headers.Authorization = `Bearer ${tok}`;
  const res = await fetch(path, { ...opts, headers });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error((data && (data.detail || data.error)) || `HTTP ${res.status}`);
  return data;
}

export async function getCatalog() {
  if (_catalog) return _catalog;
  try {
    _catalog = await jfetch(`${ROOT}/catalog`);
  } catch {
    _catalog = FALLBACK_CATALOG;
  }
  return _catalog;
}

export function levelFor(xp, levels) {
  const list = levels && levels.length ? levels : FALLBACK_CATALOG.levels;
  let cur = list[0];
  for (const l of list) if (xp >= l.xp_required) cur = l;
  const next = list.find((l) => l.xp_required > xp) || null;
  const span = next ? next.xp_required - cur.xp_required : 1;
  return {
    level: cur.level,
    name: cur.name,
    floor: cur.xp_required,
    next: next ? next.xp_required : 0,
    progress: next ? Math.min(100, Math.max(0, ((xp - cur.xp_required) / span) * 100)) : 100,
  };
}

function readLocal() {
  try {
    const raw = JSON.parse(localStorage.getItem(LS_KEY) || "null");
    if (raw && typeof raw === "object") return raw;
  } catch {}
  return { xp: 0, counters: {}, achievements: {}, recent: [], streak: 0, last_active: null };
}

function writeLocal(state) {
  try { localStorage.setItem(LS_KEY, JSON.stringify(state)); } catch {}
}

function shapeLocal(raw, catalog, extra = {}) {
  const levels = catalog?.levels || FALLBACK_CATALOG.levels;
  const lv = levelFor(raw.xp || 0, levels);
  const total = (catalog?.achievements || []).length || 12;
  return {
    ok: true,
    source: "local",
    xp: raw.xp || 0,
    level: lv.level,
    level_name: lv.name,
    next_level_xp: lv.next,
    xp_to_next: lv.next ? Math.max(0, lv.next - (raw.xp || 0)) : 0,
    progress: lv.progress,
    streak: raw.streak || 0,
    last_active: raw.last_active || null,
    counters: raw.counters || {},
    achievements: raw.achievements || {},
    achievements_unlocked: Object.keys(raw.achievements || {}).length,
    achievements_total: total,
    recent: (raw.recent || []).slice(-20),
    new_achievements: [],
    ...extra,
  };
}

export async function getState() {
  try {
    const s = await jfetch(`${ROOT}/state`);
    writeLocal({ xp: s.xp, counters: s.counters, achievements: s.achievements, recent: s.recent, streak: s.streak, last_active: s.last_active });
    return s;
  } catch {
    const catalog = await getCatalog();
    return shapeLocal(readLocal(), catalog);
  }
}

export async function award(event, { amount, meta } = {}) {
  try {
    const s = await jfetch(`${ROOT}/award`, {
      method: "POST",
      body: JSON.stringify({ event, amount, meta, user_id: "operator" }),
    });
    writeLocal({ xp: s.xp, counters: s.counters, achievements: s.achievements, recent: s.recent, streak: s.streak, last_active: s.last_active });
    return s;
  } catch {
    const catalog = await getCatalog();
    const raw = readLocal();
    const def = (catalog.events || FALLBACK_CATALOG.events)[event] || { xp: 0, metric: "misc" };
    const gain = typeof amount === "number" ? amount : def.xp || 0;
    raw.xp = (raw.xp || 0) + gain;
    raw.counters = { ...(raw.counters || {}) };
    raw.counters[def.metric] = (raw.counters[def.metric] || 0) + 1;
    const today = new Date().toISOString().slice(0, 10);
    if (raw.last_active !== today) raw.streak = (raw.streak || 0) + 1;
    raw.last_active = today;
    raw.recent = [...(raw.recent || []), { event, xp: gain, at: Date.now() / 1000 }].slice(-40);
    writeLocal(raw);
    const state = shapeLocal(raw, catalog, { awarded: gain, event });
    return state;
  }
}

export async function resetState() {
  try {
    const s = await jfetch(`${ROOT}/reset`, { method: "POST" });
    writeLocal({ xp: 0, counters: {}, achievements: {}, recent: [], streak: 0, last_active: null });
    return s;
  } catch {
    localStorage.removeItem(LS_KEY);
    const catalog = await getCatalog();
    return shapeLocal(readLocal(), catalog);
  }
}

/** Fire-and-forget XP event consumed by the XP bar. */
export function emitXp(event, detail = {}) {
  if (!event) return;
  window.dispatchEvent(new CustomEvent("xxxgpt:xp", { detail: { event, ...detail } }));
}
