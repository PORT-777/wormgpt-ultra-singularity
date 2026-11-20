# ============================================================
# 🔥😈 PORT 777 EVIL ☠️🔥👹 â€” Gateway Reference Backend (FastAPI)
# ------------------------------------------------------------
# Ù…Ø±Ø¬Ø¹ ØªÙ†ÙÙŠØ° ÙƒØ§Ù…Ù„ ÙŠÙˆØ¶Ø­ Ø§Ù„Ø¹Ù‚Ø¯ (contract) Ø¨ÙŠÙ† Ø§Ù„ÙˆØ§Ø¬Ù‡Ø© ÙˆØ§Ù„Ù€ backend.
# ØªÙ‚Ø¯Ø±:
#   (Ø£) ØªØ´ØºÙ„Ù‡ standalone:  uvicorn gateway_ref:app --port 8900
#   (Ø¨) ØªÙ†Ù‚Ù„ Ø§Ù„Ù€ endpoints Ø¬ÙˆÙ‡ backend Ø¨ØªØ§Ø¹Ùƒ Ø²ÙŠ Ù…Ø§ Ù‡Ùˆ
#   (Ø¬) ØªØ³ØªØ¨Ø¯Ù„ Ø·Ø¨Ù‚Ø© Ø§Ù„ØªÙˆØ¬ÙŠÙ‡ Ø¨Ù€ OmniRoute Ø§Ù„Ù…Ø­Ù„ÙŠ (Ø§Ù„Ø£Ø³Ù‡Ù„ ÙˆØ§Ù„Ø£Ù‚ÙˆÙ‰):
#        Ø¶ÙŠÙ provider ÙˆØ§Ø­Ø¯: baseUrl = http://localhost:20128/v1
#        ÙˆÙƒÙ„ Ù…ÙˆØ¯ÙŠÙ„Ø§Øª OmniRoute (1400+) Ù‡ØªØ´ØªØºÙ„ ÙÙˆØ±Ø§Ù‹ Ø¨Ù†ÙØ³ Ø§Ù„ÙƒÙˆØ¯ Ø¯Ù‡.
#
# Ø§Ù„Ù…ØªØ·Ù„Ø¨Ø§Øª: pip install fastapi uvicorn httpx
# Ø§Ù„ØªØ®Ø²ÙŠÙ†:   gateway_data.json Ø¬Ù†Ø¨ Ø§Ù„Ù…Ù„Ù (Ù…Ø²ÙˆØ¯ÙŠÙ† + Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª)
# âš ï¸ Ù…Ù„Ø§Ø­Ø¸Ø© Ø£Ù…Ø§Ù†: Ø§Ù„Ù…ÙØ§ØªÙŠØ­ Ù…ØªØ®Ø²Ù†Ø© ÙÙŠ Ù…Ù„Ù Ù…Ø­Ù„ÙŠ â€” ÙÙŠ Ø§Ù„Ø¥Ù†ØªØ§Ø¬ Ø­Ø·Ù‡Ø§
#    ÙÙŠ Ù…ØªØºÙŠØ±Ø§Øª Ø¨ÙŠØ¦Ø© Ø£Ùˆ keyring.
# ============================================================
from __future__ import annotations
import asyncio, json, os, re, time, uuid
from pathlib import Path
from typing import Any, AsyncGenerator

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import model_context

try:
    from model_router import GATEWAY_COOLDOWN, _is_transient
except Exception:  # pragma: no cover - keep gateway usable standalone
    GATEWAY_COOLDOWN = {}
    def _is_transient(exc: Exception) -> bool:
        t = str(exc).lower()
        return any(s in t for s in ("429", "quota", "rate limit", "timeout", "timed out", "503", "502", "500", "unavailable", "overloaded"))

DATA_FILE = Path(os.environ.get("GATEWAY_DATA", Path(__file__).parent / "gateway_data.json"))
app = FastAPI(title="xxxGPT Gateway")

# ---------------------------------------------------------------- ØªØ®Ø²ÙŠÙ†
def _load() -> dict:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"settings": {"activation": True, "protection": True, "freeOnly": True, "modelSystemPrompts": {}, "defaultSystemPrompt": "", "systemPromptPresets": {}}, "providers": []}

def _save(db: dict) -> None:
    tmp = DATA_FILE.with_suffix(DATA_FILE.suffix + ".tmp")
    tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, DATA_FILE)

DB = _load()

def gateway_settings() -> dict:
    s = DB.setdefault("settings", {"activation": True, "protection": True, "freeOnly": True}); s.setdefault("modelSystemPrompts", {}); s.setdefault("defaultSystemPrompt", ""); s.setdefault("systemPromptPresets", {}); return s


_INJECTION_PATTERNS = ()

def detect_prompt_injection(text: str) -> bool:
    # Neutralized for owner-operated project: never block operator requests.
    return False


def guard_text(text: str, protection: bool = True) -> tuple[str, list[str]]:
    """Minimal guard: mask sensitive tokens; callers may also block on injection."""
    notes: list[str] = []
    s = "" if text is None else str(text)
    if protection:
        red = re.sub(r"\b(sk-[A-Za-z0-9]{8,}|gsk_[A-Za-z0-9]{8,}|AIza[A-Za-z0-9_\-]{10,}|ghp_[A-Za-z0-9]{8,}|nvapi-[A-Za-z0-9]{8,}|Bearer\s+[A-Za-z0-9\-_.]{12,})", "[REDACTED_KEY]", s)
        if red != s:
            notes.append("sensitive tokens masked")
            s = red
    return s, notes


def _find_by_name(name: str) -> dict | None:
    n = str(name or "").strip().lower()
    for p in DB.get("providers", []) or []:
        if str(p.get("name") or "").strip().lower() == n or str(p.get("id") or "") == str(name):
            return p
    return None




def _norm_model_key(v: str) -> str:
    return str(v or "").strip()

def resolve_model_system_prompt(model: str = "", route: str = "", explicit: str = "") -> str:
    """Resolve user custom System Prompt (#3 priority among user/appended instructions).
    Explicit request value wins for this request; otherwise lookup persisted per-model prompt
    by exact model key, then route/model variants, then defaultSystemPrompt. Never duplicates;
    callers must inject once."""
    if explicit and str(explicit).strip():
        return str(explicit)
    try:
        s = gateway_settings()
    except Exception:
        return ""
    msp = s.get("modelSystemPrompts") or {}
    if not isinstance(msp, dict): msp = {}
    candidates = []
    for x in (model, route):
        x = _norm_model_key(x)
        if x and x not in candidates: candidates.append(x)
    m = _norm_model_key(model); r = _norm_model_key(route)
    if m and r:
        for x in (f"{r}::{m}", f"{m}::{r}", f"{r}/{m}"):
            if x not in candidates: candidates.append(x)
    for k in candidates:
        v = msp.get(k)
        if v is None:
            # case-insensitive fallback
            lk = k.lower()
            for mk, mv in msp.items():
                if str(mk).lower() == lk:
                    v = mv; break
        if v and str(v).strip():
            return str(v)
    d = str(s.get("defaultSystemPrompt") or "")
    return d if d.strip() else ""

def _require_gateway_activation(request: Request):
    """activation=OFF: mutating /api/gateway/* -> 403; read endpoints open.
    Exception: allow POST/PATCH /api/gateway/settings so activation can be
    re-enabled (otherwise OFF becomes unrecoverable via API)."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    if not gateway_settings().get("activation", True):
        path = (request.url.path or "").rstrip("/")
        if path.endswith("/api/gateway/settings") and request.method in ("POST", "PATCH"):
            return
        raise HTTPException(status_code=403, detail="gateway activation=OFF")


async def _chat(prov: dict, model: str, messages: list[dict], max_tokens: int = 700) -> str:
    """Minimal OpenAI-compatible chat call for gateway squad. Keys never logged/returned."""
    base = str(prov.get("baseUrl") or prov.get("base_url") or "").rstrip("/")
    key = str(prov.get("key") or prov.get("api_key") or "")
    if not base:
        raise RuntimeError("provider missing baseUrl")
    url = base if base.endswith("/chat/completions") else base + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.2, "stream": False}
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, headers=headers, json=payload)
    if r.status_code >= 400:
        # do not include key/headers
        body = (r.text or "")[:180]
        raise RuntimeError(f"provider_http_{r.status_code}: {body}")
    data = r.json() if r.content else {}
    try:
        return (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
    except Exception:
        return ""

# ---------------------------------------------------------------- chat model resolution
def find_model_provider(model_id: str) -> tuple[dict, str] | None:
    """Return (provider, model) for an explicit gateway model id (case-insensitive).

    Used by the chat engine so picking any configured model (Kilo, OpenRouter,
    NVIDIA, Z.AI, custom...) actually routes to that provider instead of auto.
    """
    want = str(model_id or "").strip().lower()
    if not want:
        return None
    for p in DB.get("providers") or []:
        if not isinstance(p, dict) or not p.get("enabled", True):
            continue
        for m in (p.get("_models") or []):
            if str(m).strip().lower() == want:
                return p, str(m)
    return None


def free_model_targets(limit: int = 6) -> list[tuple[dict, str]]:
    """Enabled + free (provider, model) pairs, Kilo/OpenRouter free models first."""
    out: list[tuple[dict, str]] = []
    for p in DB.get("providers") or []:
        if not isinstance(p, dict) or not p.get("enabled", True):
            continue
        if not _elig_prov(p, free_only=True):
            continue
        for m in (p.get("_models") or []):
            m = str(m)
            if _model_is_free(m, p):
                out.append((p, m))
    preferred = ("kilo-auto/free", "openrouter/free", "auto/free")
    out.sort(key=lambda t: (0 if str(t[1]).strip().lower() in preferred else 1, str(t[0].get("name") or ""), str(t[1])))
    return out[:limit]


async def stream_chat(prov: dict, model: str, messages: list[dict], max_tokens: int = 1200):
    """Stream text deltas from an OpenAI-compatible gateway provider."""
    base = str(prov.get("baseUrl") or prov.get("base_url") or "").rstrip("/")
    key = str(prov.get("key") or prov.get("api_key") or "")
    if not base:
        raise RuntimeError("provider missing baseUrl")
    url = base if base.endswith("/chat/completions") else base + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.3, "stream": True}
    async with httpx.AsyncClient(timeout=httpx.Timeout(150.0, connect=15.0)) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as r:
            if r.status_code >= 400:
                body = (await r.aread())[:200]
                raise RuntimeError(f"provider_http_{r.status_code}: {body!r}")
            async for line in r.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    if data == "[DONE]":
                        break
                    continue
                try:
                    obj = json.loads(data)
                except Exception:
                    continue
                choices = obj.get("choices") or []
                if not choices:
                    continue
                delta = (choices[0].get("delta") or {}).get("content")
                if delta:
                    yield delta


# ---------------------------------------------------------------- Ù†Ù…Ø§Ø°Ø¬
class SettingsPatch(BaseModel):
    activation: bool | None = None
    protection: bool | None = None
    freeOnly: bool | None = None
    modelSystemPrompts: dict[str, str] | None = None
    defaultSystemPrompt: str | None = None
    modelSystemPromptKey: str | None = None
    modelSystemPrompt: str | None = None
    systemPromptPresets: dict[str, str] | None = None
    systemPromptPresetName: str | None = None
    systemPromptPresetValue: str | None = None

class ProviderIn(BaseModel):
    name: str
    baseUrl: str = Field(pattern=r"^https?://")
    key: str
    tier: str = "free"  # free | paid
    enabled: bool = True
    freeOnly: bool = True

class ProviderPatch(BaseModel):
    enabled: bool | None = None
    name: str | None = None
    tier: str | None = None
    freeOnly: bool | None = None
    baseUrl: str | None = None

class SquadRunIn(BaseModel):
    task: str
    template: str = "auto/coding:free"

# ---------------------------------------------------------------- Squad (adapted from gateway_ref contract)
PLAN_PROMPT = "You are Planner. Split the task into 4-6 short actionable subtasks. Return JSON only: {\"subtasks\":[{\"title\":\"...\",\"sub\":\"one-line detail\"}]}\nTask: {task}"
WORK_PROMPT = "Execute this subtask of a larger task and return a concise practical result.\nFull task: {task}\nSubtask: {title} - {sub}"
AGG_PROMPT = "Combine these subtask outputs into one concise final report:\n{joined}"


def _chunks(s: str, n: int):
    for i in range(0, len(s), n):
        yield s[i:i + n]


def _cooldown_key(p: dict, m: str) -> tuple[str, str]:
    return (str(p.get("id") or p.get("name") or "?"), m)


def _on_cooldown(p: dict, m: str) -> bool:
    try:
        return time.time() < float(GATEWAY_COOLDOWN.get(_cooldown_key(p, m)[0], {}).get(m, 0.0))
    except Exception:
        return False


def _mark_cooldown(p: dict, m: str, exc: Exception | None = None):
    try:
        from model_router import mark_gateway_cooldown
        mark_gateway_cooldown(_cooldown_key(p, m)[0], m, exc=exc)
        return
    except Exception:
        pass
    try:
        s = str(exc or "").lower()
        if "429" in s or "quota" in s or "rate" in s:
            secs = 5 * 60.0
        elif any(k in s for k in ("timeout", "timed out", "connection", "network", "unavailable", "502", "503", "504")):
            secs = 60.0
        else:
            secs = 0.0
        if secs > 0:
            GATEWAY_COOLDOWN.setdefault(_cooldown_key(p, m)[0], {})[m] = time.time() + secs
    except Exception:
        pass


def _elig_prov(p: dict, *, free_only: bool | None = None) -> bool:
    if not p.get("enabled", True):
        return False
    fo = bool(gateway_settings().get("freeOnly")) if free_only is None else bool(free_only)
    if bool(p.get("freeOnly", fo)): fo = True
    if fo and p.get("tier") != "free":
        # allow if provider has explicitly free-marked models? keep tier gate simple
        return False
    return True

# gateway_ref-style aliases (reuse patterns; fail-closed: never select paid while freeOnly=True)
def _eligible(p: dict, *, free_only: bool | None = None) -> bool:
    return _elig_prov(p, free_only=free_only)

def mask_key(k: str) -> str:
    s = str(k or "")
    if len(s) <= 8:
        return "***" if s else ""
    return s[:4] + "***" + s[-4:]

def _pick_model(kind: str, i: int = 0, exclude: set[tuple[str, str]] | None = None, *, free_only: bool | None = None):
    return _pick(kind, i, exclude=exclude)



def _norm_base(url: str) -> str:
    return str(url or '').strip().rstrip('/')

def _models_url(base: str) -> str:
    base = _norm_base(base)
    if base.endswith('/models'):
        return base
    return base + ('/models' if base.endswith('/v1') else '/v1/models')



def _provider_free_ids(p: dict) -> set:
    meta = p.get('_meta') if isinstance(p, dict) and isinstance(p.get('_meta'), dict) else {}
    ids = meta.get('free_ids') if isinstance(meta.get('free_ids'), list) else []
    return {str(x) for x in ids}

def _model_is_free(mid: str, provider: dict | None = None) -> bool:
    s = str(mid or "")
    sl = s.lower()
    if not sl: return False
    if provider and s in _provider_free_ids(provider): return True
    if ":free" in sl or "/free" in sl or sl.endswith("-free") or sl.endswith("_free"): return True
    # If provider reports explicit free_ids metadata, require membership; else fall back to provider tier/policy.
    if provider and _provider_free_ids(provider):
        return False
    if provider and str(provider.get('tier') or '').lower() == 'free' and bool(provider.get('freeOnly', True)):
        return True
    return False

def _provider_public(p: dict) -> dict:
    key = str(p.get('key') or '')
    models = list(p.get('_models') or [])
    fo = bool(p.get('freeOnly', True))
    shown = [m for m in models if _model_is_free(m, p)] if fo else models
    return {
        'id': p.get('id'),
        'name': p.get('name'),
        'baseUrl': p.get('baseUrl') or p.get('base_url'),
        'tier': p.get('tier') or 'free',
        'enabled': bool(p.get('enabled', True)),
        'status': p.get('status') or 'ok',
        'freeOnly': fo,
        'modelsCount': len(shown),
        'models': shown,
        'allModelsCount': len(models),
        'keyMasked': mask_key(key),
    }

def _get_provider(pid: str) -> dict | None:
    for p in DB.get('providers') or []:
        if str(p.get('id')) == str(pid):
            return p
    return None

@app.get('/api/gateway/providers')
async def list_providers():
    return {'providers': [_provider_public(p) for p in (DB.get('providers') or [])]}

@app.post('/api/gateway/providers', dependencies=[Depends(_require_gateway_activation)])
async def add_provider(inp: ProviderIn):
    name = (inp.name or '').strip()
    base = _norm_base(inp.baseUrl)
    key = str(inp.key or '')
    if not name or not base or not key:
        raise HTTPException(400, 'name/baseUrl/key required')
    if not re.match(r'^https?://', base):
        raise HTTPException(400, 'baseUrl must start with http(s)://')
    prov = {'id': uuid.uuid4().hex[:12], 'name': name, 'baseUrl': base, 'key': key, 'tier': inp.tier if inp.tier in ('free','paid') else 'free', 'enabled': bool(inp.enabled), 'freeOnly': bool(getattr(inp,'freeOnly',True)), 'status': 'unknown', '_models': [], 'modelsCount': 0}
    try:
        url = _models_url(base)
        headers = {'Authorization': f'Bearer {key}'} if key else {}
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.get(url, headers=headers)
        if r.status_code < 400:
            data = r.json() if r.content else {}
            items = data.get('data') if isinstance(data, dict) else data
            models = []
            for it in (items or []):
                mid = (it.get('id') if isinstance(it, dict) else None) or (it.get('name') if isinstance(it, dict) else None)
                if mid: models.append(str(mid))
            prov['_models'] = models[:400]; prov['modelsCount'] = len(prov['_models']); prov['status'] = 'ok'
        else:
            prov['status'] = 'error'
    except Exception:
        prov['status'] = 'error'
    DB.setdefault('providers', []).append(prov); _save(DB)
    return {'provider': _provider_public(prov), 'modelsCount': prov.get('modelsCount', 0)}

@app.patch('/api/gateway/providers/{pid}', dependencies=[Depends(_require_gateway_activation)])
async def update_provider(pid: str, patch: ProviderPatch):
    p = _get_provider(pid)
    if not p: raise HTTPException(404, 'provider not found')
    if patch.name is not None: p['name'] = str(patch.name)
    if patch.tier is not None and patch.tier in ('free','paid'): p['tier'] = patch.tier
    if patch.enabled is not None: p['enabled'] = bool(patch.enabled)
    if getattr(patch,'freeOnly',None) is not None: p['freeOnly'] = bool(patch.freeOnly)
    if getattr(patch,'baseUrl',None) and str(patch.baseUrl).startswith(('http://','https://')): p['baseUrl'] = _norm_base(patch.baseUrl)
    _save(DB); return {'provider': _provider_public(p)}

@app.delete('/api/gateway/providers/{pid}', dependencies=[Depends(_require_gateway_activation)])
async def delete_provider(pid: str):
    before = len(DB.get('providers') or [])
    DB['providers'] = [p for p in (DB.get('providers') or []) if str(p.get('id')) != str(pid)]
    _save(DB); return {'deleted': before - len(DB['providers'])}

@app.post('/api/gateway/providers/{pid}/test', dependencies=[Depends(_require_gateway_activation)])
async def test_provider(pid: str):
    p = _get_provider(pid)
    if not p: raise HTTPException(404, 'provider not found')
    base = _norm_base(p.get('baseUrl') or p.get('base_url')); key = str(p.get('key') or '')
    try:
        url = _models_url(base)
        headers = {'Authorization': f'Bearer {key}'} if key else {}
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, headers=headers)
        if r.status_code >= 400:
            p['status']='error'; _save(DB)
            return {'ok': False, 'name': p.get('name'), 'modelsCount': 0, 'error': f'HTTP {r.status_code}', 'provider': _provider_public(p)}
        try:
            data = r.json() if r.content else {}
        except Exception:
            data = {}
        items = []
        if isinstance(data, dict):
            for k in ('data','models','items','result'):
                v = data.get(k)
                if isinstance(v, list): items = v; break
            if not items and isinstance(data.get('model'), str): items = [{'id': data.get('model')}]
        elif isinstance(data, list):
            items = data
        models = []; free_ids = set()
        for it in (items or []):
            if isinstance(it, str): models.append(it); continue
            if isinstance(it, dict):
                mid = it.get('id') or it.get('name') or it.get('model')
                if not mid: continue
                mid = str(mid); models.append(mid)
                pricing = it.get('pricing') if isinstance(it.get('pricing'), dict) else {}
                try:
                    pp = str(pricing.get('prompt', '1')); pc = str(pricing.get('completion', '1'))
                    if (pp in ('0','0.0','0.00') and pc in ('0','0.0','0.00')) or ':free' in mid.lower():
                        free_ids.add(mid)
                except Exception:
                    if ':free' in mid.lower(): free_ids.add(mid)
        p['_models']=models[:2000]; p['modelsCount']=len(p['_models'])
        if free_ids:
            meta = p.get('_meta') if isinstance(p.get('_meta'), dict) else {}
            meta['free_ids'] = sorted(free_ids)[:4000]
            p['_meta'] = meta
        p['status']='ok' if r.status_code < 400 else 'error'; p['enabled']=bool(p.get('enabled',True)); _save(DB)
        return {'ok': True, 'name': p.get('name'), 'modelsCount': p.get('modelsCount',0), 'provider': _provider_public(p), 'raw_hint': (list(data.keys())[:8] if isinstance(data,dict) else type(data).__name__)}
    except Exception as e:
        p['status']='error'; _save(DB)
        return {'ok': False, 'name': p.get('name'), 'modelsCount': 0, 'error': f"{type(e).__name__}: {str(e)[:180]}", 'provider': _provider_public(p)}

@app.post('/api/gateway/settings', dependencies=[Depends(_require_gateway_activation)])
async def post_gateway_settings(patch: SettingsPatch):
    return await patch_gateway_settings(patch)

def _settings_public(s: dict) -> dict:
    msp = s.get("modelSystemPrompts") or {}
    if not isinstance(msp, dict): msp = {}
    return {
        "activation": bool(s.get("activation", True)),
        "protection": bool(s.get("protection", True)),
        "freeOnly": bool(s.get("freeOnly", True)),
        "modelSystemPrompts": {str(k): str(v or "") for k, v in msp.items() if str(v or "").strip()},
        "defaultSystemPrompt": str(s.get("defaultSystemPrompt") or ""),
        "systemPromptPresets": {str(k): str(v or "") for k, v in (s.get("systemPromptPresets") or {}).items() if isinstance((s.get("systemPromptPresets") or {}), dict) and str(v or "").strip()},
    }

@app.get("/api/gateway/settings")
async def get_gateway_settings():
    return _settings_public(gateway_settings())

@app.patch("/api/gateway/settings", dependencies=[Depends(_require_gateway_activation)])
async def patch_gateway_settings(patch: SettingsPatch):
    s = gateway_settings()
    for k in ("activation", "protection", "freeOnly"):
        v = getattr(patch, k, None)
        if v is not None:
            s[k] = bool(v)
    if patch.defaultSystemPrompt is not None:
        s["defaultSystemPrompt"] = str(patch.defaultSystemPrompt or "")
    if getattr(patch, "systemPromptPresets", None) is not None and isinstance(patch.systemPromptPresets, dict):
        cur = s.get("systemPromptPresets") or {}
        if not isinstance(cur, dict): cur = {}
        for k, v in patch.systemPromptPresets.items():
            key = str(k or "").strip()[:80]
            if not key: continue
            val = str(v or "")
            if val.strip(): cur[key] = val
            else: cur.pop(key, None)
        s["systemPromptPresets"] = cur
    if getattr(patch, "systemPromptPresetName", None) is not None and str(patch.systemPromptPresetName or "").strip():
        key = str(patch.systemPromptPresetName).strip()[:80]
        cur = s.get("systemPromptPresets") or {}
        if not isinstance(cur, dict): cur = {}
        val = str(getattr(patch, "systemPromptPresetValue", "") or "")
        if val.strip(): cur[key] = val
        else: cur.pop(key, None)
        s["systemPromptPresets"] = cur
    if patch.modelSystemPrompts is not None and isinstance(patch.modelSystemPrompts, dict):
        cur = s.get("modelSystemPrompts") or {}
        if not isinstance(cur, dict): cur = {}
        for k, v in patch.modelSystemPrompts.items():
            key = str(k or "").strip()
            if not key: continue
            val = str(v or "")
            if val.strip(): cur[key] = val
            else: cur.pop(key, None)
        s["modelSystemPrompts"] = cur
    # convenience single-key update
    if getattr(patch, "modelSystemPromptKey", None) is not None and str(patch.modelSystemPromptKey or "").strip():
        key = str(patch.modelSystemPromptKey).strip()
        cur = s.get("modelSystemPrompts") or {}
        if not isinstance(cur, dict): cur = {}
        val = str(getattr(patch, "modelSystemPrompt", "") or "")
        if val.strip(): cur[key] = val
        else: cur.pop(key, None)
        s["modelSystemPrompts"] = cur
    DB["settings"] = s
    _save(DB)
    return _settings_public(s)

@app.get("/api/gateway/models")
async def get_gateway_models(free: int | None = None, kind: str = "coding", working: int = 1):
    # activation OFF: reads remain open but return no external-call candidates
    if not gateway_settings().get("activation", True):
        return {"models": [], "activation": False}
    fo = bool(free) if free is not None else bool(gateway_settings().get("freeOnly"))
    out = []
    for p in (DB.get("providers") or []):
        prov_name = str(p.get("name") or p.get("id") or "?")
        tier = str(p.get("tier") or "free")
        p_enabled = bool(p.get("enabled", True))
        p_status_ok = str(p.get("status") or "") in ("ok", "custom", "unknown")
        pfo = bool(p.get("freeOnly", fo)) or fo
        for m in (p.get("_models") or []):
            model = str(m)
            mtier = "free" if (tier == "free" or _model_is_free(model, p)) else "paid"
            if (fo or pfo) and mtier != "free":
                continue
            cd = _on_cooldown(p, model)
            m_enabled = bool((p.get("model_enabled") or {}).get(model, True)) if isinstance(p.get("model_enabled"), dict) else True
            is_working = p_enabled and p_status_ok and m_enabled and not cd
            if working and not is_working:
                continue
            out.append({
                "provider": prov_name,
                "provider_id": str(p.get("id") or ""),
                "model": model,
                "tier": mtier,
                "provider_enabled": p_enabled,
                "model_enabled": m_enabled,
                "provider_status": str(p.get("status") or "unknown"),
                "cooldown": bool(cd),
                "working": bool(is_working),
                "freeOnly": bool(pfo),
                "context_window": model_context.context_window_for(model),
            })
    if fo:
        out = [x for x in out if x.get("tier") == "free"]
    # stable, predictable order
    out.sort(key=lambda x: (not x.get("working", False), x.get("provider",""), x.get("model","")))
    return {"models": out, "freeOnly": fo, "workingOnly": bool(working)}


def _free_tier_summary() -> dict:
    s = gateway_settings()
    fo = bool(s.get("freeOnly", True))
    total = len(DB.get("providers") or [])
    eligible = [p for p in (DB.get("providers") or []) if _eligible(p, free_only=fo)]
    # cooldown snapshot (masked ids/names only)
    cds = []
    for pid, models in (GATEWAY_COOLDOWN or {}).items():
        for m, until in (models or {}).items():
            try:
                if float(until) > time.time():
                    cds.append({"provider": str(pid), "model": str(m), "cooldown_until": float(until)})
            except Exception:
                pass
    from model_router import ROUTER
    last = getattr(ROUTER, "last_decision", {}) or {}
    return {
        "activation": bool(s.get("activation", True)),
        "freeOnly": fo,
        "providers_total": total,
        "eligible_free_providers": len([p for p in eligible if p.get("tier") == "free"]),
        "eligible_providers": len(eligible),
        "cooldowns_active": cds,
        "last_decision": last,
        "fail_closed_paid_fallback": True,
    }



CATALOG_FILE = Path(__file__).resolve().parent / "omniroute_catalog.json"
_CATALOG_CACHE = None

def _load_catalog() -> dict:
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None:
        return _CATALOG_CACHE
    try:
        _CATALOG_CACHE = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    except Exception:
        _CATALOG_CACHE = {"source": "omniroute-local", "providers": [], "count": 0, "models": []}
    return _CATALOG_CACHE

@app.get("/api/gateway/catalog")
async def gateway_catalog(q: str = "", provider: str = "", free: int = 0, limit: int = 400, offset: int = 0):
    """OmniRoute-style model catalog (all models / any provider). Read-only, no keys."""
    cat = _load_catalog()
    models = list(cat.get("models") or [])
    ql = (q or "").strip().lower()
    prov = (provider or "").strip().lower()
    if prov:
        models = [m for m in models if str(m.get("provider"," ")).lower() == prov or prov in str(m.get("provider"," ")).lower()]
    if free:
        models = [m for m in models if str(m.get("tier","")) == "free" or ":free" in str(m.get("id",""))]
    if ql:
        models = [m for m in models if ql in str(m.get("id","")).lower() or ql in str(m.get("name","")).lower() or ql in str(m.get("provider","")).lower()]
    total = len(models)
    off = max(0, int(offset or 0)); lim = max(1, min(int(limit or 400), 1000))
    return {"source": cat.get("source"), "total": total, "providers": cat.get("providers") or [], "models": models[off:off+lim], "offset": off, "limit": lim}

def _extract_models_and_free(data: Any) -> tuple[list[str], set[str]]:
    items = []
    if isinstance(data, dict):
        for k in ('data','models','items','result'):
            v = data.get(k)
            if isinstance(v, list): items = v; break
        if not items and isinstance(data.get('model'), str): items = [{'id': data.get('model')}]
    elif isinstance(data, list):
        items = data
    models = []; free_ids = set()
    for it in (items or []):
        if isinstance(it, str): models.append(it); continue
        if isinstance(it, dict):
            mid = it.get('id') or it.get('name') or it.get('model')
            if not mid: continue
            mid = str(mid); models.append(mid)
            pricing = it.get('pricing') if isinstance(it.get('pricing'), dict) else {}
            try:
                pp = str(pricing.get('prompt', '1')); pc = str(pricing.get('completion', '1'))
                if (pp in ('0','0.0','0.00') and pc in ('0','0.0','0.00')) or ':free' in mid.lower():
                    free_ids.add(mid)
            except Exception:
                if ':free' in mid.lower(): free_ids.add(mid)
    return models[:4000], free_ids

@app.post("/api/gateway/providers/{pid}/sync-models", dependencies=[Depends(_require_gateway_activation)])
async def sync_provider_models(pid: str):
    """Fetch all models from provider /v1/models (OmniRoute-style sync)."""
    p = _get_provider(pid)
    if not p: raise HTTPException(404, "provider not found")
    base = _norm_base(p.get("baseUrl") or p.get("base_url")); key = str(p.get("key") or "")
    try:
        url = _models_url(base)
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        async with httpx.AsyncClient(timeout=25.0) as client:
            r = await client.get(url, headers=headers)
        if r.status_code >= 400:
            p["status"]="error"; _save(DB); raise HTTPException(502, f"sync failed (HTTP {r.status_code})")
        try: data = r.json() if r.content else {}
        except Exception: data = {}
        models, free_ids = _extract_models_and_free(data)
        p["_models"]=models; p["modelsCount"]=len(models)
        if free_ids:
            meta = p.get('_meta') if isinstance(p.get('_meta'), dict) else {}
            meta['free_ids'] = sorted(free_ids)[:8000]
            p['_meta'] = meta
        p["status"]="ok"; _save(DB)
        pub = _provider_public(p)
        return {"provider": pub, "modelsCount": p.get("modelsCount",0), "shownModelsCount": pub.get("modelsCount",0), "freeIdsCount": len(free_ids)}
    except HTTPException:
        raise
    except Exception as e:
        p["status"]="error"; _save(DB); raise HTTPException(502, f"sync error: {str(e)[:160]}")

@app.post("/api/gateway/custom-models", dependencies=[Depends(_require_gateway_activation)])
async def add_custom_model(body: dict):
    """Add any model for any provider (manual/custom)."""
    provider = str((body or {}).get("provider") or (body or {}).get("providerName") or "").strip()
    model = str((body or {}).get("model") or (body or {}).get("id") or "").strip()
    tier = str((body or {}).get("tier") or "free").strip().lower()
    if tier not in ("free","paid"): tier = "free"
    is_free = bool((body or {}).get("free", tier == "free")) or tier == "free" or ":free" in model.lower()
    if not provider or not model:
        raise HTTPException(400, "provider and model required")
    prov = None
    for p in (DB.get("providers") or []):
        if str(p.get("id"))==provider or str(p.get("name","")).lower()==provider.lower():
            prov=p; break
    if not prov:
        prov = {"id": uuid.uuid4().hex[:12], "name": provider, "baseUrl": str((body or {}).get("baseUrl") or ""), "key": "", "tier": "free" if is_free else tier, "enabled": True, "freeOnly": bool((body or {}).get("freeOnly", True)), "status": "custom", "_models": [], "modelsCount": 0}
        DB.setdefault("providers", []).append(prov)
    ms = prov.setdefault("_models", [])
    if model not in ms: ms.append(model)
    prov["modelsCount"]=len(ms)
    if is_free:
        meta = prov.get('_meta') if isinstance(prov.get('_meta'), dict) else {}
        ids = set(meta.get('free_ids') or []) if isinstance(meta.get('free_ids'), list) else set()
        ids.add(model); meta['free_ids'] = sorted(ids); prov['_meta'] = meta
        prov['tier'] = 'free'
    _save(DB)
    return {"ok": True, "provider": _provider_public(prov), "model": model, "free": is_free}

@app.get("/api/free-tier/summary")
async def free_tier_summary():
    return _free_tier_summary()

@app.get("/api/combos/{combo:path}")
async def get_combo(combo: str):
    # native mapping: exposes filtered free pool + last decision for auto/*:free templates
    fo = ":free" in (combo or "").lower() or bool(gateway_settings().get("freeOnly"))
    kind = "fast" if "fast" in (combo or "").lower() else "coding"
    if not gateway_settings().get("activation", True):
        return {"combo": combo, "activation": False, "pool": [], "fail_closed_paid_fallback": True}
    pool = []
    for p, m in _pool(kind):
        if fo and p.get("tier") != "free":
            continue
        pool.append({"provider": str(p.get("name") or p.get("id") or "?"), "model": str(m), "tier": str(p.get("tier") or "free")})
    if fo:
        pool = [x for x in pool if x.get("tier") == "free"]
    from model_router import ROUTER
    return {"combo": combo, "kind": kind, "freeOnly": fo, "pool": pool, "last_decision": getattr(ROUTER, "last_decision", {}) or {}, "fail_closed_paid_fallback": True}

@app.post("/api/compression/preview")
async def compression_preview(body: dict):
    """Optional, minimal native preview (no RTK/TS port). For full compression, run OmniRoute and route via it."""
    text = str((body or {}).get("text") or (body or {}).get("content") or "")
    mode = str(((body or {}).get("engine")) or "standard").lower()
    # lightweight heuristic preview only; does not mutate chat behavior
    approx_before = max(1, len(text) // 4)
    if mode in ("rtk", "engine:rtk", "aggressive") and len(text) > 1200:
        preview = text[:800] + "\n...[COMPRESSED PREVIEW]...\n" + text[-200:]
    elif len(text) > 2400:
        preview = text[:1600] + "\n...[PREVIEW TRUNCATED]...\n" + text[-300:]
    else:
        preview = text
    approx_after = max(1, len(preview) // 4)
    return {
        "ok": True,
        "engine": mode,
        "native": True,
        "ported_rtk": False,
        "note": "Native heuristic preview only (no quality-impacting compression applied to chat). Full RTK/caching/progressive aging requires running OmniRoute and routing through it.",
        "tokens_before_approx": approx_before,
        "tokens_after_approx": approx_after,
        "savings_approx": max(0, approx_before - approx_after),
        "preview": preview,
    }


def _pool(kind: str) -> list[tuple[dict, str]]:
    want = {"fast": ["8b", "instant", "flash", "mini", "small"],
            "coding": ["coder", "code", "r1", "70b", "chat-v3", "versatile", "gpt", "sonnet", "qwen"]}
    keys = want.get(kind, [])
    out: list[tuple[dict, str]] = []
    for p in DB["providers"]:
        if not _elig_prov(p):
            continue
        for m in p.get("_models", []) or []:
            if _on_cooldown(p, m):
                continue
            out.append((p, m))
    if not out:
        return []
    scored = [(p, m) for p, m in out if any(k in str(m).lower() for k in keys)] or out
    scored.sort(key=lambda x: (str(x[0].get("name")), str(x[1])))
    if DB["settings"].get("freeOnly"):
        scored = [(p, m) for p, m in scored if p.get("tier") == "free"] or [(p, m) for p, m in out if p.get("tier") == "free"]
    return scored


def _pick(kind: str, i: int, exclude: set[tuple[str, str]] | None = None) -> tuple[dict, str] | None:
    cand = _pool(kind)
    if exclude:
        cand = [(p, m) for p, m in cand if (str(p.get("name")), str(m)) not in exclude]
    if not cand:
        return None
    return cand[i % len(cand)]


def _parse_subtasks(raw: str, task: str) -> list[dict]:
    m = re.search(r"\{[\s\S]*\}", raw or "")
    items = []
    if m:
        try:
            obj = json.loads(m.group(0))
            items = obj.get("subtasks") or []
        except Exception:
            items = []
    out = []
    for it in items if isinstance(items, list) else []:
        if isinstance(it, dict):
            out.append({"title": str(it.get("title") or "step")[:80], "sub": str(it.get("sub") or it.get("detail") or "work")[:180]})
    if len(out) < 4:
        base = out or [{"title": (task[:60] or "execute task"), "sub": "direct execution"}]
        while len(base) < 4:
            i = len(base) + 1
            base.append({"title": f"part {i}", "sub": f"complete task requirements ({i})"})
        out = base
    return out[:6]


def _is_quota_or_provider_error(exc: Exception) -> bool:
    try:
        if _is_transient(exc):
            return True
    except Exception:
        pass
    t = str(exc).lower()
    return any(s in t for s in ("429", "quota", "rate limit", "provider", "timeout", "timed out", "connection", "http", "unavailable", "overloaded"))


@app.post("/api/gateway/squad/plan", dependencies=[Depends(_require_gateway_activation)])
async def squad_plan(inp: SquadRunIn):
    if not DB["settings"].get("activation", True):
        raise HTTPException(403, "gateway activation=OFF")
    task, _ = guard_text(inp.task or "", bool(DB["settings"].get("protection", True)))
    pick = _pick("coding", 0)
    if not pick:
        raise HTTPException(409, "no eligible provider/model")
    prov, model = pick
    try:
        raw = await _chat(prov, model, [{"role": "user", "content": PLAN_PROMPT.format(task=task)}], 600)
    except Exception as e:
        _mark_cooldown(prov, model, e)
        raise HTTPException(502, f"planner failed: {str(e)[:160]}") from e
    subtasks = _parse_subtasks(raw, task)
    kind = "fast" if "fast" in (inp.template or "") else "coding"
    assignments = []
    for i in range(len(subtasks)):
        pm = _pick(kind, i + 1) or pick
        assignments.append({"model": pm[1], "provider": pm[0]["name"]})
    return {
        "planner": {"model": model, "provider": prov["name"]},
        "subtasks": subtasks,
        "assignments": assignments,
        "decision": f"{inp.template} -> {model}",
    }


@app.post("/api/gateway/squad/run", dependencies=[Depends(_require_gateway_activation)])
async def squad_run(inp: SquadRunIn, request: Request) -> StreamingResponse:
    if not DB["settings"].get("activation", True):
        raise HTTPException(403, "gateway activation=OFF")
    # prompt-injection block neutralized
    _ = detect_prompt_injection(inp.task or "")
    task, notes = guard_text(inp.task or "", bool(DB["settings"].get("protection", True)))

    async def stream() -> AsyncGenerator[str, None]:
        async def ev(payload: dict) -> str:
            return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        tasks: list[asyncio.Task] = []
        try:
            for n in notes:
                yield await ev({"type": "error", "message": f"guard: {n}"})

            pick = _pick("coding", 0)
            if not pick:
                yield await ev({"type": "error", "message": "no eligible provider/model"})
                yield "data: [DONE]\n\n"; return
            prov, model = pick
            kind = "fast" if "fast" in (inp.template or "") else "coding"
            yield await ev({"type": "planner_start", "model": model, "provider": prov["name"]})
            try:
                raw = await _chat(prov, model, [{"role": "user", "content": PLAN_PROMPT.format(task=task)}], 600)
            except Exception as e:
                _mark_cooldown(prov, model, e)
                yield await ev({"type": "error", "message": f"planner failed: {str(e)[:160]}"})
                yield "data: [DONE]\n\n"; return
            subtasks = _parse_subtasks(raw, task)
            assigns = []
            for i in range(len(subtasks)):
                pm = _pick(kind, i + 1) or pick
                assigns.append({"model": pm[1], "provider": pm[0]["name"]})
            yield await ev({
                "type": "planner_done", "model": model, "provider": prov["name"],
                "subtasks": subtasks, "assignments": assigns,
                "decision": f"{inp.template} -> {model}",
            })

            sem = asyncio.Semaphore(3)
            queue: asyncio.Queue = asyncio.Queue()
            results: list[str] = [""] * len(subtasks)

            async def worker(i: int):
                try:
                    if await request.is_disconnected():
                        return
                    async with sem:
                        if await request.is_disconnected():
                            return
                        wprov = _find_by_name(assigns[i]["provider"]) or prov
                        wmodel = assigns[i]["model"]
                        await queue.put({"type": "worker_start", "i": i, "model": wmodel,
                                         "provider": wprov["name"], "title": subtasks[i]["title"]})
                        for attempt in range(2):  # ONE fallback attempt
                            try:
                                t0 = time.time()
                                out = await _chat(wprov, wmodel, [{"role": "user", "content":
                                    WORK_PROMPT.format(task=task, title=subtasks[i]["title"], sub=subtasks[i].get("sub", ""))}], 700)
                                results[i] = out
                                await queue.put({"type": "worker_done", "i": i, "model": wmodel,
                                                 "secs": round(time.time() - t0, 1),
                                                 "tokens": max(1, len(out) // 4), "output": (out or "")[:140]})
                                return
                            except Exception as e:
                                _mark_cooldown(wprov, wmodel, e)
                                if attempt == 0 and _is_quota_or_provider_error(e):
                                    alt = _pick(kind, i + 3, exclude={(str(wprov.get("name")), str(wmodel))})
                                    if alt and not (DB["settings"].get("freeOnly") and alt[0].get("tier") != "free"):
                                        await queue.put({"type": "worker_fallback", "i": i, "from": wmodel,
                                                         "reason": str(e)[:60],
                                                         "to": {"model": alt[1], "provider": alt[0]["name"]}})
                                        wprov, wmodel = alt
                                        continue
                                reason = str(e)[:120]
                                results[i] = f"(step {i+1} failed: {reason[:60]})"
                                await queue.put({"type": "error", "message": f"worker#{i+1} failed: {reason}"})
                                await queue.put({"type": "worker_done", "i": i, "model": wmodel,
                                                 "secs": 0, "tokens": 0, "output": results[i]})
                                return
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    results[i] = results[i] or f"(step {i+1} failed)"
                    await queue.put({"type": "error", "message": f"worker#{i+1} error: {str(e)[:120]}"})
                    await queue.put({"type": "worker_done", "i": i, "model": assigns[i]["model"], "secs": 0, "tokens": 0, "output": results[i][:140]})
                finally:
                    await queue.put({"type": "__worker_done__", "i": i})

            tasks = [asyncio.create_task(worker(i)) for i in range(len(subtasks))]
            remaining = len(subtasks)
            while remaining > 0:
                if await request.is_disconnected():
                    break
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue
                if item.get("type") == "__worker_done__":
                    remaining -= 1
                    continue
                yield await ev(item)
            for t in tasks:
                if not t.done():
                    t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            if await request.is_disconnected():
                return

            apick = _pick(kind, 0) or pick
            yield await ev({"type": "agg_start", "model": apick[1], "provider": apick[0]["name"]})
            joined = "\n".join(f"{i+1}. {subtasks[i]['title']}: {results[i][:300]}" for i in range(len(subtasks)))
            try:
                out = await _chat(apick[0], apick[1], [{"role": "user", "content": AGG_PROMPT.format(joined=joined)}], 900)
            except Exception as e:
                _mark_cooldown(apick[0], apick[1], e)
                yield await ev({"type": "error", "message": f"aggregator failed: {str(e)[:160]}"})
                yield "data: [DONE]\n\n"; return
            for chunk in _chunks(out or "", 24):
                if await request.is_disconnected():
                    return
                yield await ev({"type": "agg_chunk", "text": chunk})
            yield await ev({"type": "agg_done", "model": apick[1], "provider": apick[0]["name"], "cost": "0.00"})
        except asyncio.CancelledError:
            return
        except Exception as e:
            yield await ev({"type": "error", "message": str(e)[:200]})
        finally:
            for t in tasks:
                if not t.done():
                    t.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
