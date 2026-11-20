# backend/api/main.py
# Language: Python 3 | Runtime: CPython | Target: Windows 11
# 🔥😈 PORT 777 EVIL ☠️🔥👹 - Singularity Edition â€” FastAPI API Layer.
# Ù†Ù‚Ø§Ø·: /run (ØªØ´ØºÙŠÙ„ Ù…Ù‡Ø§Ù…) /trace /ws/trace (WebSocket ØªØ±Ù„Ø§Ø«) /health (Ø­ÙŠ)
#       /v1/chat/completions (Ù…ØªÙˆØ§ÙÙ‚Ø© OpenAI) /api/models

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # backend/
from tools import execute_tool, tool_schemas, TOOL_REGISTRY
from backend.agent_engine import ENGINE
from model_router import ROUTER
import configs as config

app = FastAPI(title="🔥😈 PORT 777 EVIL ☠️🔥👹 - Singularity Edition API")

# open-webui Ù†Ù…Ø·: CORS Ù…ÙØªÙˆØ­ Ù„Ù„ÙˆØ§Ø¬Ù‡Ø© (Ù…Ø­Ù„ÙŠØ§Ù‹ _) + Ø±ÙØ¹ Ù…Ù„ÙØ§Øª Ø¥Ù„Ù‰ workspace
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from security_api import router as _security_router
    app.include_router(_security_router)
except Exception as _exc:  # pragma: no cover - keep the app bootable
    import logging as _logging
    _logging.getLogger("api.main").warning("CyberOps API not mounted: %s", _exc)

connected: List[WebSocket] = []

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "workspace" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/upload")
async def upload_file(file: UploadFile):
    """Ø§Ù„ÙˆØ§Ø¬Ù‡Ø© ØªØ±Ø³Ù„ Ù…Ù„ÙØ§Ù‹ (Ù†Ù…Ø· open-webui)Ø› ÙŠÙØ®Ø²Ù‘Ù† ÙÙŠ workspace/uploads."""
    safe_name = Path(file.filename or "upload.bin").name
    dest = UPLOAD_DIR / safe_name
    data = await file.read()
    if len(data) > 50 * 1024 * 1024:
        return JSONResponse({"error": "file > 50MB"}, status_code=413)
    dest.write_bytes(data)
    rel = dest.relative_to(UPLOAD_DIR.parents[1])
    return JSONResponse({"ok": True, "path": str(rel).replace("\\", "/"),
                         "size": len(data)})

Orchestrator = None
try:
    from main import SingularityOrchestrator
    Orchestrator = SingularityOrchestrator()
except Exception as _exc:
    _ORCH_ERROR = _exc


async def broadcast(msg: Dict[str, Any]) -> None:
    data = json.dumps(msg, ensure_ascii=False, default=str)
    dead = []
    for ws in connected:
        try:
            await ws.send_text(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in connected:
            connected.remove(ws)


# ===================================================================== #
#  Core endpoints
# ===================================================================== #
@app.post("/run")
async def run_task(payload: Dict[str, Any]):
    desc = payload.get("description", "api_task")
    ctx = payload.get("context", {})
    try:
        result = await execute_tool(ctx.get("op", "chain"), ctx)
    except Exception as exc:
        result = f"ERROR: {type(exc).__name__}: {exc}"
    await broadcast({"type": "task_result", "description": desc, "result": result})
    return JSONResponse({"status": "done", "result": result})


@app.get("/trace")
async def get_trace():
    if Orchestrator is None:
        return JSONResponse({"trace": [f"orchestrator unavailable: {_ORCH_ERROR}"]}, status_code=503)
    return JSONResponse({"trace": Orchestrator.trace().splitlines()})


# ===================================================================== #
#  OpenAI-compatible surface (Ù…Ø³ØªØ¹Ø§Ø± Ù…Ù† AIClient2API)
# ===================================================================== #
@app.get("/health")
async def health():
    """ÙØ­Øµ Ø­ÙŠØ© Ù„Ù„Ù…Ø²ÙˆØ¯ÙŠÙ† + Ø¥Ø­ØµØ§Ø¦ÙŠØ§Øª."""
    snap = ROUTER.status()
    return JSONResponse({
        "ok": any(v.get("available") for v in snap.values()),
        "time": round(time.time(), 2),
        "engine_state": ENGINE.status if ENGINE else "unavailable",
        "providers": snap,
        "tools": sorted(TOOL_REGISTRY.keys()),
    })


@app.get("/api/models")
async def list_models():
    """Ù„Ø§Ø¦Ø­Ø© ÙƒÙ„ canvas Ø§Ù„Ù…ÙˆØ¯ÙŠÙ„Ø§Øª Ø§Ù„Ù…ØªØ§Ø­Ø© Ù„ÙƒÙ„ Ù…Ø²ÙˆØ¯ (Ù†Ù…Ø· AIClient2API)."""
    return JSONResponse(ROUTER.status())


@app.get("/api/skills")
async def list_skills():
    """Ù„Ø§Ø¦Ø­Ø© skill packs Ø§Ù„Ù…Ø­Ù…Ù„Ø© (superpowers-style SKILL.md)."""
    try:
        from skills import load_packs
        packs = load_packs()
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
    return JSONResponse({"count": len(packs), "packs": [
        {"name": p["name"], "description": p["description"],
         "always": p["always"], "triggers": p["trigger_when"]}
        for p in packs]})


# ===================================================================== #
#  Findings ledger (Ù†Ù…Ø· strix): Ø³Ø¬Ù„ Ø«ØºØ±Ø§Øª Ù…Ù†Ø¸Ù… + ØªÙ‚Ø±ÙŠØ± Ø¬Ø§Ù‡Ø²
# ===================================================================== #
import findings as findings_store
import engagement as engagement_store
from fastapi.responses import Response


# --------------------------------------------------------------------------- #
#  Engagement state (strix threat_model + coverage + notes port)
# --------------------------------------------------------------------------- #
@app.get("/engagement")
async def engagement_summary():
    """Ø§Ù„Ø­Ø§Ù„Ø© Ø§Ù„Ù…Ø´ØªØ±ÙƒØ© Ù„Ù„Ù…Ù‡Ù…Ø© Ø§Ù„Ø£Ù…Ù†ÙŠØ©: Ù†Ù…ÙˆØ°Ø¬ Ø§Ù„ØªÙ‡Ø¯ÙŠØ¯ + Ø§Ù„ØªØºØ·ÙŠØ© + Ø§Ù„Ù…Ù„Ø§Ø­Ø¸Ø§Øª."""
    return JSONResponse(engagement_store.summary())


@app.post("/engagement/threat-model")
async def engagement_save_threat_model(payload: Dict[str, Any]):
    """Ø§ÙƒØªØ¨ Ù†Ù…ÙˆØ°Ø¬ Ø§Ù„ØªÙ‡Ø¯ÙŠØ¯ Ø§Ù„ÙƒØ§Ù…Ù„ Ù„Ù„Ù‡Ø¯Ù {target, content} (ÙŠØ³ØªØ¨Ø¯Ù„ ÙˆÙŠÙ…Ø³Ø­ Ø§Ù„Ø¥Ø¶Ø§ÙØ§Øª)."""
    r = engagement_store.save_threat_model(
        str(payload.get("target") or ""),
        str(payload.get("content") or ""),
        author=str(payload.get("author") or "operator"))
    return JSONResponse(r, status_code=200 if r.get("ok") else 400)


@app.post("/engagement/amend")
async def engagement_amend_threat_model(payload: Dict[str, Any]):
    """Ø£Ø¶Ù ØªØµØ­ÙŠØ­/ØªÙˆØ³Ø¹Ø© Ù„Ù†Ù…ÙˆØ°Ø¬ Ø§Ù„ØªÙ‡Ø¯ÙŠØ¯ {target, addendum} (append-only)."""
    r = engagement_store.amend_threat_model(
        str(payload.get("target") or ""),
        str(payload.get("addendum") or ""),
        author=str(payload.get("author") or "operator"))
    return JSONResponse(r, status_code=200 if r.get("ok") else 400)


@app.get("/engagement/threat-model")
async def engagement_get_threat_model(target: str = ""):
    """Ø§Ù‚Ø±Ø£ Ù†Ù…ÙˆØ°Ø¬ Ø§Ù„ØªÙ‡Ø¯ÙŠØ¯ Ø§Ù„Ù…Ø·Ø¨Ù‘Ø¹ Ù„Ù„Ù‡Ø¯Ù ?target=."""
    return JSONResponse(engagement_store.get_threat_model(target))


@app.post("/engagement/coverage")
async def engagement_record_coverage(payload: Dict[str, Any]):
    """Ø³Ø¬Ù‘Ù„ ØµÙ ØªØºØ·ÙŠØ© {surface, risk_area, outcome, evidence}."""
    r = engagement_store.record_coverage(
        str(payload.get("surface") or ""),
        str(payload.get("risk_area") or ""),
        str(payload.get("outcome") or ""),
        str(payload.get("evidence") or ""),
        author=str(payload.get("author") or "operator"))
    return JSONResponse(r, status_code=200 if r.get("ok") else 400)


@app.put("/engagement/coverage/{entry_id}")
async def engagement_update_coverage(entry_id: str, payload: Dict[str, Any]):
    """Ø­Ø¯Ù‘Ø« Ù†ØªÙŠØ¬Ø© ØµÙ Ù…ÙˆØ¬ÙˆØ¯ {outcome, evidence} â€” Ø§Ù„ØªØ§Ø±ÙŠØ® Ø§Ù„Ù‚Ø¯ÙŠÙ… Ù…Ø­ÙÙˆØ¸."""
    r = engagement_store.update_coverage(
        entry_id,
        str(payload.get("outcome") or ""),
        str(payload.get("evidence") or ""),
        author=str(payload.get("author") or "operator"))
    return JSONResponse(r, status_code=200 if r.get("ok") else 400)


@app.post("/engagement/notes")
async def engagement_add_note(payload: Dict[str, Any]):
    """Ø£Ø¶Ù Ù…Ù„Ø§Ø­Ø¸Ø© Ø¹Ù…Ù„ {kind, text}."""
    return JSONResponse(engagement_store.add_note(
        str(payload.get("kind") or "observation"),
        str(payload.get("text") or ""),
        author=str(payload.get("author") or "operator")))


@app.delete("/engagement")
async def engagement_clear():
    engagement_store.clear()
    return JSONResponse({"ok": True})


@app.get("/findings")
async def findings_list():
    """Ø³Ø¬Ù„ Ø§Ù„Ø«ØºØ±Ø§Øª Ø§Ù„Ù…Ø¤ÙƒØ¯Ø© Ù…Ø¹ Ø¹Ø¯Ù‘Ø§Ø¯ ÙƒÙ„ Ø¯Ø±Ø¬Ø© Ø®Ø·ÙˆØ±Ø©."""
    return JSONResponse({
        "count": len(findings_store.list_all()),
        "counts": findings_store.counts(),
        "findings": findings_store.list_all(),
    })


@app.post("/findings")
async def findings_add(payload: Dict[str, Any]):
    """Ø³Ø¬Ù‘Ù„ Ø«ØºØ±Ø© ÙˆØ§Ø­Ø¯Ø© {title, severity, target, owasp, evidence, poc, remediation}."""
    item = findings_store.add(payload)
    await broadcast({"type": "finding", "data": item})
    return JSONResponse({"ok": True, "finding": item})


@app.delete("/findings")
async def findings_clear():
    findings_store.clear()
    return JSONResponse({"ok": True})


@app.get("/findings/report.md")
async def findings_report():
    """ØªÙ‚Ø±ÙŠØ± Ø§Ø®ØªØ¨Ø§Ø± Ø£Ù…Ù†ÙŠ Ø¬Ø§Ù‡Ø² (markdown) â€” Ù†Ù…Ø· penetration_test_report."""
    md = findings_store.report_md()
    return Response(
        content=md, media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition":
                 'attachment; filename="🔥😈 PORT 777 EVIL ☠️🔥👹_pentest_report.md"'})


@app.get("/findings/report.sarif")
async def findings_sarif():
    """SARIF 2.1.0 â€” ØªÙƒØ§Ù…Ù„ GitHub code scanning (Ù†Ù…Ø· findings.sarif)."""
    return JSONResponse(findings_store.sarif())


@app.get("/findings/report.csv")
async def findings_csv():
    """CSV (UTF-8-BOM) â€” ÙŠÙØªØ­ ÙÙŠ Excel Ù…Ø¨Ø§Ø´Ø±Ø© (Ù†Ù…Ø· findings.csv)."""
    return Response(
        content=findings_store.report_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition":
                 'attachment; filename="findings.csv"'})


@app.get("/findings/report.html")
async def findings_html():
    """ØªÙ‚Ø±ÙŠØ± HTML ØªÙØ§Ø¹Ù„ÙŠ Ø¯Ø§ÙƒÙ† RTL (Ù†Ù…Ø· ØªÙ‚Ø±ÙŠØ± strix)."""
    return Response(content=findings_store.report_html(),
                    media_type="text/html; charset=utf-8")


@app.get("/findings/report.zip")
async def findings_zip():
    """Ø­Ø²Ù…Ø© Ø§Ù„Ø£Ø±ØªÙŠÙØ§ÙƒØªØ³ ÙƒØ§Ù…Ù„Ø© (Ù†Ù…Ø· strix_runs/<run>/) â€” md + html +
    vulnerabilities/*.md + json + sarif + csv ÙÙŠ Ù…Ù„Ù ÙˆØ§Ø­Ø¯."""
    return Response(
        content=findings_store.report_zip(),
        media_type="application/zip",
        headers={"Content-Disposition":
                 'attachment; filename="🔥😈 PORT 777 EVIL ☠️🔥👹_findings_bundle.zip"'})


@app.get("/findings/vuln/{index}.md")
async def findings_vuln_md(index: int):
    """Ø«ØºØ±Ø© ÙˆØ§Ø­Ø¯Ø© ÙƒÙ…Ù„Ù Ù…Ø³ØªÙ‚Ù„ (Ù†Ù…Ø· strix vulnerabilities/0001-x.md)."""
    md = findings_store.vuln_md(index)
    if not md:
        return JSONResponse({"error": "finding not found"}, status_code=404)
    return Response(content=md, media_type="text/markdown; charset=utf-8")


@app.get("/openai/v1/models")
@app.get("/v1/models")
async def openai_models():
    """Ù‚Ø§Ø¦Ù…Ø© Ø±Ù…Ø²ÙŠØ© Ù…ØªÙˆØ§ÙÙ‚Ø© OpenAI: id ÙˆØ§Ø­Ø¯Ø© Ù„ÙƒÙ„ Ù…Ø²ÙˆØ¯ Ù†Ø´Ø·."""
    snap = ROUTER.status()
    data = []
    for name, st in snap.items():
        if st.get("available"):
            data.append({"id": name, "object": "model",
                         "active_model": st.get("active")})
    return JSONResponse({"object": "list", "data": data})


@app.post("/v1/chat/completions")
async def openai_chat_completions(req: Dict[str, Any]):
    """Ù…ØªÙˆØ§ÙÙ‚Ø© OpenAI: ÙŠØªØ±Ø¬Ù… requested messages Ø¥Ù„Ù‰ run Ø¹Ø¨Ø± Ø§Ù„Ù…Ø­Ø±Ùƒ Ø§Ù„ÙƒØ§Ù…Ù„
    (ReAct-E: plan â†’ loop â†’ reflect â†’ persist â†’ final) ÙˆÙŠØ¹ÙŠØ¯ Ø§Ù„Ø´ÙƒÙ„ Ø§Ù„Ù‚ÙŠØ§Ø³ÙŠ."""
    # Ø¢Ø®Ø± Ø±Ø³Ø§Ù„Ø© Ù…Ù† Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù… Ù‡Ùˆ Ø§Ù„Ù‡Ø¯ÙØ› Ù…Ø§ Ù‚Ø¨Ù„Ù‡Ø§ ÙŠØµØ¨Ø­ history ÙƒØ§Ù…Ù„
    raw_messages = req.get("messages") or []
    messages = [m for m in raw_messages if isinstance(m, dict)]
    if not messages:
        return JSONResponse({"error": {"message": "messages required", "type": "bad_request"}}, status_code=400)
    user = ""
    history: List[Dict] = []
    prior = messages[:-1]
    for m in prior:
        role = m.get("role", "")
        content = str(m.get("content", "")).strip()
        if role in ("user", "assistant") and content:
            history.append({"role": role, "content": content})
    for m in reversed(messages):
        if m.get("role") == "user":
            user = str(m.get("content", "")).strip()
            break

    if ENGINE is None:
        return JSONResponse({"error": {"message": "engine unavailable", "type": "server_error"}}, status_code=503)

    full_access = bool(req.get("🔥😈 PORT 777 EVIL ☠️🔥👹_full_access", False))
    depth = str(req.get("depth") or "standard").lower()
    if depth not in ("quick", "standard", "deep"):
        depth = "standard"
    if not user:
        return JSONResponse({"error": {"message": "no user message", "type": "bad_request"}}, status_code=400)

    system_prompt = str(req.get("system_prompt") or req.get("systemPrompt") or "").strip() or None
    try:
        if not system_prompt:
            from gateway import resolve_model_system_prompt as _resolve_msp
            system_prompt = _resolve_msp(model=str(req.get("model") or "auto"), route="auto", explicit="") or None
    except Exception:
        pass
    # ---------------- Live SSE stream (open-webui style) ---------------- #
    if req.get("stream"):
        async def sse():
            try:
                async for ev in ENGINE.run_stream(
                    user, history=history or None,
                    model_route="auto", model_name=str(req.get("model") or "auto"),
                    full_access=full_access, depth=depth,
                    system_prompt=system_prompt,
                ):
                    yield f"data: {json.dumps(ev, default=str, ensure_ascii=False)}\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'type': 'error', 'data': f'{type(exc).__name__}: {exc}'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(
            sse(), media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    parts: List[str] = []
    final_answer = ""
    try:
        async for event in ENGINE.run_stream(
            user, history=history or None, model_route="auto",
            model_name=str(req.get("model") or "auto"),
            full_access=full_access, depth=depth,
            system_prompt=system_prompt,
        ):
            kind = event.get("type", "")
            data = event.get("data")
            if kind == "stream" and data:
                parts.append(str(data))
            elif kind == "final" and data:
                final_answer = str(data)
    except Exception as exc:
        log = None
        return JSONResponse({
            "error": {"message": f"engine failure: {type(exc).__name__}: {exc}",
                      "type": "server_error"}}, status_code=502)
    answer = "".join(parts).strip() or final_answer.strip() \
        or "Agent finished without streaming a Final Answer."

    await broadcast({"type": "openai_call", "model": "🔥😈 PORT 777 EVIL ☠️🔥👹-ultra",
                     "user": user[:300], "answer": answer[:300]})
    return JSONResponse({
        "id": f"chatcmpl-{int(time.time() * 1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "🔥😈 PORT 777 EVIL ☠️🔥👹-ultra",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": answer},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    })


# ===================================================================== #
#  WebSocket live trace
# ===================================================================== #
@app.websocket("/ws/trace")
async def ws_trace(ws: WebSocket):
    await ws.accept()
    connected.append(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        if ws in connected:
            connected.remove(ws)


# ---------------- static frontend (last, catch-all) ---------------- #
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR),
                               html=True), name="frontend")
