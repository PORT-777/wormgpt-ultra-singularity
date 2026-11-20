"""Real image understanding (vision) with provider fallback.

Used by:
  * the model-facing `Vision` tool (screenshots, photos, diagrams)
  * /api/chat when the user attaches an image

No fake success: every candidate provider is called for real; the first
working answer wins.  If every provider fails the caller gets an explicit
error listing what was tried.

Providers (env-driven, best-effort order):
  1. OpenRouter  - any vision model id, default free VL model
  2. Gemini      - only when the key looks like a real AI Studio key (AIza...)
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import mimetypes
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import configs as config

log = logging.getLogger("vision")

MAX_IMAGE_BYTES = 10 * 1024 * 1024          # 10 MB hard cap
DEFAULT_QUESTION = ("Describe this image in detail: visible text, UI state, "
                    "errors, people/objects, diagrams and anything an "
                    "assistant would need to reason about it.")
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
DEFAULT_OPENROUTER_MODELS = (
    "nvidia/nemotron-3.5-super-vl:free,"
    "inclusionai/ling-3.2-flash:free,"
    "google/gemma-4-31b-it:free"
)

_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_TTL = 300.0


# --------------------------------------------------------------------- #
#  helpers
# --------------------------------------------------------------------- #
def is_image(path: str | Path) -> bool:
    p = Path(path)
    if p.suffix.lower() in IMAGE_EXTS:
        return True
    mime, _ = mimetypes.guess_type(p.name)
    return bool(mime and mime.startswith("image/"))


def _mime_for(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    if mime and mime.startswith("image/"):
        return mime
    return {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp",
    }.get(path.suffix.lower(), "image/png")


def _read_b64(path: Path) -> str:
    data = path.read_bytes()
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"image too large ({len(data)} bytes > {MAX_IMAGE_BYTES})")
    return base64.b64encode(data).decode()


def _cache_get(key: str) -> Optional[Dict[str, Any]]:
    hit = _CACHE.get(key)
    if not hit:
        return None
    ts, val = hit
    if time.time() - ts > _CACHE_TTL:
        _CACHE.pop(key, None)
        return None
    return val


def _cache_put(key: str, val: Dict[str, Any]) -> None:
    if len(_CACHE) > 200:
        _CACHE.clear()
    _CACHE[key] = (time.time(), val)


# --------------------------------------------------------------------- #
#  provider candidates
# --------------------------------------------------------------------- #
def _openrouter_candidates() -> List[Tuple[str, str]]:
    if not getattr(config, "OPENROUTER_READY", False):
        return []
    raw = os.getenv("VISION_OPENROUTER_MODELS", DEFAULT_OPENROUTER_MODELS)
    out: List[Tuple[str, str]] = []
    for mid in str(raw).split(","):
        mid = mid.strip()
        if mid:
            out.append((mid, "openrouter"))
    return out


def _gemini_candidates() -> List[Tuple[str, str]]:
    key = str(getattr(config, "GEMINI_API_KEY", "") or "")
    # Real AI Studio keys start with "AIza". OAuth tokens ("AQ....") are not
    # accepted by generativelanguage and only waste a request.
    if not key.startswith("AIza"):
        return []
    models = [getattr(config, "GEMINI_MODEL", ""),
              *getattr(config, "GEMINI_MODEL_FALLBACKS", [])]
    return [(str(m).strip(), "gemini") for m in models if str(m).strip()]


def _post_json(url: str, payload: dict, headers: dict,
               timeout: float) -> dict:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json",
                                          **headers})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _openrouter_call(model: str, data_url: str, question: str,
                     timeout: float) -> str:
    key = str(getattr(config, "OPENROUTER_API_KEY", "") or "")
    out = _post_json(
        "https://openrouter.ai/api/v1/chat/completions",
        {
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }],
            "max_tokens": 500,
            "temperature": 0.2,
        },
        {"Authorization": f"Bearer {key}"},
        timeout,
    )
    choices = out.get("choices") or []
    if not choices:
        raise RuntimeError(f"no choices in response: {str(out)[:200]}")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if isinstance(content, list):
        content = " ".join(str(c.get("text", "")) if isinstance(c, dict) else str(c)
                           for c in content)
    content = str(content or "").strip()
    if not content:
        raise RuntimeError("empty completion")
    return content


def _gemini_call(model: str, b64: str, mime: str, question: str,
                 timeout: float) -> str:
    key = str(getattr(config, "GEMINI_API_KEY", "") or "")
    base = str(os.getenv("GEMINI_BASE_URL",
                         "https://generativelanguage.googleapis.com/v1beta")
               or "").rstrip("/")
    url = f"{base}/models/{model}:generateContent?key={key}"
    out = _post_json(url, {
        "contents": [{
            "parts": [
                {"text": question},
                {"inline_data": {"mime_type": mime, "data": b64}},
            ],
        }],
        "generationConfig": {"maxOutputTokens": 500, "temperature": 0.2},
    }, {}, timeout)
    cands = out.get("candidates") or []
    if not cands:
        raise RuntimeError(f"no candidates: {str(out)[:200]}")
    parts = ((cands[0].get("content") or {}).get("parts") or [])
    text = " ".join(str(p.get("text", "")) for p in parts).strip()
    if not text:
        raise RuntimeError("empty completion")
    return text


# --------------------------------------------------------------------- #
#  public API
# --------------------------------------------------------------------- #
def describe_image(path: str | Path, question: str = "",
                   timeout: float = 45.0) -> Dict[str, Any]:
    """Describe one image. Never raises for provider failures."""
    p = Path(path)
    q = str(question or DEFAULT_QUESTION).strip() or DEFAULT_QUESTION
    if not p.is_file():
        return {"ok": False, "error": f"no such image: {p}"}
    try:
        digest = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    except Exception as exc:
        return {"ok": False, "error": f"cannot read image: {exc}"}
    key = f"{digest}|{q[:120]}"
    cached = _cache_get(key)
    if cached:
        return cached

    try:
        b64 = _read_b64(p)
        mime = _mime_for(p)
        data_url = f"data:{mime};base64,{b64}"
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    tried: List[str] = []
    for model, provider in (_openrouter_candidates()
                            + _gemini_candidates()):
        label = f"{provider}:{model}"
        tried.append(label)
        try:
            if provider == "openrouter":
                text = _openrouter_call(model, data_url, q, timeout)
            else:
                text = _gemini_call(model, b64, mime, q, timeout)
            result = {"ok": True, "text": text, "provider": provider,
                      "model": model, "tried": tried}
            _cache_put(key, result)
            return result
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:160]
            except Exception:
                pass
            log.warning("[vision] %s failed: HTTP %s %s", label, exc.code, detail)
        except Exception as exc:
            log.warning("[vision] %s failed: %s", label, exc)

    return {"ok": False,
            "error": ("all vision providers failed: " + ", ".join(tried)
                      if tried else "no vision provider configured "
                      "(set OPENROUTER_API_KEY or a real AIza... GEMINI_API_KEY)"),
            "tried": tried}


def describe_images(paths: List[str | Path], question: str = "",
                    timeout: float = 45.0) -> Dict[str, Any]:
    """Describe many images; returns aggregate + per-image detail."""
    items: List[Dict[str, Any]] = []
    chunks: List[str] = []
    for raw in paths:
        p = Path(raw)
        res = describe_image(p, question, timeout=timeout)
        item = {"path": str(p), "name": p.name, **res}
        items.append(item)
        if res.get("ok"):
            chunks.append(f"[{p.name}]\n{res['text']}")
        else:
            chunks.append(f"[{p.name}] vision unavailable: {res.get('error')}")
    ok = any(i.get("ok") for i in items)
    provider = next((i.get("provider") for i in items if i.get("ok")), None)
    model = next((i.get("model") for i in items if i.get("ok")), None)
    return {"ok": ok, "text": "\n\n".join(chunks), "items": items,
            "provider": provider, "model": model}