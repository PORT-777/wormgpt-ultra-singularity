"""Internal routes for the deep AI platform capabilities.

All routes require `x-internal-key` matching INTERNAL_API_KEY (fail closed).
No frontend file calls these routes.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from external_apis.config import config as ext_config


router = APIRouter(prefix="/api/internal", tags=["ai-platform"])


def _platform_module(name: str):
    """Import a capability module even when stdlib `platform` shadows the package.

    Uvicorn started as `backend.main:app` puts the stdlib `platform` module
    ahead of our top-level `platform/` package on sys.path. Loading by file
    path makes these routes work in both launch modes.
    """
    import importlib.util
    import sys
    from pathlib import Path

    try:
        return importlib.import_module(f"platform.{name}")
    except Exception:
        path = Path(__file__).resolve().parent.parent / "platform" / f"{name}.py"
        spec = importlib.util.spec_from_file_location(f"platform_{name}", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load platform module {name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module


def _auth(key: Optional[str]) -> None:
    if not ext_config.internal_key:
        raise HTTPException(status_code=503, detail="internal services disabled")
    if key != ext_config.internal_key:
        raise HTTPException(status_code=401, detail="invalid internal key")


class TextRequest(BaseModel):
    text: str = ""
    question: str = ""
    prompt: str = ""
    source: str = ""
    top_k: int = 5
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RAGQueryRequest(BaseModel):
    question: str
    top_k: int = 5
    expand: bool = True
    diverse: bool = True


class AgentRequest(BaseModel):
    task: str
    agent: str = ""
    mode: str = "chat"
    session_id: str = ""


class DocParseRequest(BaseModel):
    source: str = ""
    content_b64: str = ""
    mime_type: str = "text/plain"


class ModelRequest(BaseModel):
    prompt: str = ""
    model: str = ""
    strategy: str = "task_optimal"
    task_type: str = ""


class ScoreRequest(BaseModel):
    question: str
    response: str
    context: List[str] = Field(default_factory=list)


class WorkflowRequest(BaseModel):
    workflow: Dict[str, Any]
    trigger_input: Any = None


# ------------------------------- RAG -------------------------------- #

@router.post("/rag/ingest")
async def rag_ingest(body: TextRequest, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from rag.pipeline import pipeline
    n = await pipeline.ingest(body.source or body.text, metadata=body.metadata)
    return {"chunks": n}


@router.post("/rag/query")
async def rag_query(body: RAGQueryRequest, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from rag.pipeline import pipeline
    r = await pipeline.query(body.question, body.top_k, body.expand, body.diverse)
    return r.__dict__


@router.get("/rag/documents")
async def rag_documents(x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from rag.pipeline import pipeline
    return {"documents": pipeline.documents()}


@router.delete("/rag/documents/{doc_id}")
async def rag_delete(doc_id: str, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from rag.pipeline import pipeline
    return {"deleted": pipeline.delete(doc_id)}


@router.post("/rag/evaluate")
async def rag_evaluate(body: TextRequest, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from rag.models import RAGResponse, Source
    from rag.pipeline import pipeline
    resp = RAGResponse(answer=body.text, sources=[Source(id="s1", excerpt=body.text)])
    metrics = await pipeline.evaluate(body.question, resp)
    return metrics.__dict__


@router.get("/rag/stats")
async def rag_stats(x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from rag.pipeline import pipeline
    return pipeline.stats()


@router.post("/rag/search")
async def rag_search(body: RAGQueryRequest, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from rag.pipeline import pipeline
    hits = await pipeline.search(body.question, body.top_k)
    return {"results": [{"chunk_id": h.chunk.chunk_id, "score": h.score,
                         "text": h.chunk.text} for h in hits]}


# ------------------------------ Agents ------------------------------ #

@router.post("/agents/run")
async def agents_run(body: AgentRequest, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from agents.orchestrator import OrchestratorAgent
    r = await OrchestratorAgent().run(body.task)
    return r.__dict__


@router.post("/agents/{name}/run")
async def agents_named(name: str, body: AgentRequest,
                       x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from agents.orchestrator import OrchestratorAgent
    agent = OrchestratorAgent().sub_agents.get(name)
    if agent is None:
        raise HTTPException(status_code=404, detail="unknown agent")
    r = await agent().run(body.task)
    return r.__dict__


@router.get("/agents/jobs/{job_id}")
async def agent_job(job_id: str, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from streaming.queue import queue
    return queue.status(job_id)


@router.get("/agents/jobs/{job_id}/result")
async def agent_job_result(job_id: str, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from streaming.queue import queue
    return queue.result(job_id)


@router.get("/agents/tools")
async def agent_tools(x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from agents.tool_registry import list_tools
    return {"tools": list_tools()}


@router.post("/agents/tools/{name}")
async def agent_tool_call(name: str, body: Dict[str, Any],
                          x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from agents.tool_registry import call_tool
    return {"result": await call_tool(name, **body)}


@router.delete("/agents/memory/{user_id}")
async def agent_memory_clear(user_id: str, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from agents.memory import memory
    memory.clear(user_id)
    return {"cleared": user_id}


# ----------------------------- Documents ---------------------------- #

@router.post("/docs/parse")
async def docs_parse(body: DocParseRequest, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    import base64
    from documents.parser import parser
    if body.content_b64:
        data = base64.b64decode(body.content_b64)
        doc = await parser.parse(data, body.mime_type)
    else:
        doc = await parser.parse(body.source, body.mime_type)
    return {"text": doc.text[:20000], "mime_type": doc.mime_type,
            "pages": len(doc.pages), "metadata": doc.metadata}


@router.post("/docs/extract/tables")
async def docs_tables(body: DocParseRequest, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from documents.parser import parser
    doc = await parser.parse(body.source, body.mime_type)
    return {"tables": [t.__dict__ for t in doc.tables]}


@router.post("/docs/classify")
async def docs_classify(body: TextRequest, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from documents.classifier import classify
    return {"type": classify(body.text).value}


@router.post("/docs/ocr")
async def docs_ocr(body: DocParseRequest, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from documents.ocr import ocr_image
    return {"text": ocr_image(body.source)}


@router.post("/docs/summarize")
async def docs_summarize(body: TextRequest, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from rag.pipeline import pipeline
    r = await pipeline.query("Summarize: " + body.text[:3000])
    return {"summary": r.answer}


@router.get("/docs/workspace")
async def docs_workspace(x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from pathlib import Path
    ws = Path("workspace")
    return {"files": [str(p) for p in ws.rglob("*") if p.is_file()][:500]}


# ------------------------------- Models ------------------------------ #

@router.get("/models/catalog")
async def models_catalog(x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from models.registry import catalog
    return {"models": catalog()}


@router.post("/models/route")
async def models_route(body: ModelRequest, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from models.router import route_request, RoutingStrategy
    from models.registry import MODEL_CATALOG
    sel = await route_request(body.prompt, body.task_type or None,
                              RoutingStrategy(body.strategy))
    return {"name": sel.name, "reason": sel.reason, "spec": sel.spec.__dict__}


@router.post("/models/call/auto")
async def models_call_auto(body: ModelRequest, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from models.fallback import call_with_fallback
    r = await call_with_fallback(body.prompt)
    return {"model": r.model, "result": r.result}


@router.get("/models/usage")
async def models_usage(x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from models.monitor import summary
    return summary()


@router.get("/models/cost")
async def models_cost(x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from models.monitor import summary
    s = summary()
    return {"total": s["total_cost"], "by_model": s["cost_by_model"]}


@router.post("/models/cache/query")
async def models_cache_query(body: TextRequest, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from models.semantic_cache import semantic_cache
    hit = await semantic_cache.get(body.prompt)
    return {"hit": bool(hit), "response": hit.response if hit else None}


@router.post("/models/cache/warm")
async def models_cache_warm(body: TextRequest, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from models.semantic_cache import semantic_cache
    count = 0
    for q in [x for x in body.text.splitlines() if x.strip()][:20]:
        await semantic_cache.set(q, "[warmed]")
        count += 1
    return {"warmed": count}


# -------------------------------- Eval ------------------------------- #

@router.get("/eval/metrics")
async def eval_metrics(period: str = "24h", x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from eval.metrics import get_metrics
    return (await get_metrics(period)).model_dump()


@router.get("/eval/traces")
async def eval_traces(limit: int = 50, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from eval.metrics import _load
    return {"traces": _load()[-limit:]}


@router.post("/eval/score")
async def eval_score(body: ScoreRequest, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from eval.scorer import score_response
    r = await score_response(body.question, body.response, body.context)
    return r.__dict__


@router.get("/eval/health/all")
async def eval_health(x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from external_apis.health import health_dashboard
    return await health_dashboard()


@router.get("/eval/cost/projection")
async def eval_projection(x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from eval.metrics import get_metrics
    m = await get_metrics("24h")
    return {"daily_usd": m.cost_today_usd, "projected_monthly_usd": round(m.cost_today_usd * 30, 6)}


# ----------------------------- Streaming ----------------------------- #

@router.get("/stream/sse/{session_id}")
async def stream_sse(session_id: str, prompt: str = "hello",
                      model: str = "auto", x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from streaming.sse import stream_llm_response
    return await stream_llm_response(prompt, model, session_id)


@router.post("/jobs/submit")
async def jobs_submit(body: Dict[str, Any], x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from streaming.queue import queue
    job_id = await queue.submit(str(body.get("task_type", "echo")),
                                dict(body.get("payload", {})))
    return {"job_id": job_id}


@router.get("/jobs/{job_id}/status")
async def jobs_status(job_id: str, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from streaming.queue import queue
    return queue.status(job_id)


@router.get("/jobs/{job_id}/result")
async def jobs_result(job_id: str, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    from streaming.queue import queue
    return queue.result(job_id)


# ------------------------------ Platform ----------------------------- #

@router.post("/workflows/run")
async def workflows_run(body: WorkflowRequest, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    Workflow = _platform_module("workflow_engine").Workflow
    execute_workflow = _platform_module("workflow_engine").execute_workflow
    r = await execute_workflow(Workflow(**body.workflow), body.trigger_input)
    return r.model_dump()


@router.post("/sessions")
async def sessions_create(body: Dict[str, Any], x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    create_session = _platform_module("chat_session").create_session
    s = create_session(str(body.get("user_id", "default")), str(body.get("model", "auto")))
    return s.model_dump()


@router.get("/sessions/{session_id}")
async def sessions_get(session_id: str, x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    get_session = _platform_module("chat_session").get_session
    s = get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    return s.model_dump()


@router.post("/workspaces")
async def workspaces_create(body: Dict[str, Any], x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    create_workspace = _platform_module("workspace").create_workspace
    ws = create_workspace(str(body.get("name", "default")))
    return ws.model_dump()


@router.get("/workspaces")
async def workspaces_list(x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    list_workspaces = _platform_module("workspace").list_workspaces
    return {"workspaces": [ws.model_dump() for ws in list_workspaces()]}


@router.post("/workspaces/{ws_id}/chat")
async def workspaces_chat(ws_id: str, body: TextRequest,
                          x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    chat = _platform_module("workspace").chat
    return await chat(ws_id, body.question or body.text)


@router.post("/code/write")
async def code_write(body: Dict[str, Any], x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    CodeEnvironment = _platform_module("code_environment").CodeEnvironment
    env = CodeEnvironment(session_id=str(body.get("session_id", "default")))
    return {"path": await env.write_file(str(body.get("path", "f.txt")),
                                         str(body.get("content", "")))}


@router.post("/code/run")
async def code_run(body: Dict[str, Any], x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    CodeEnvironment = _platform_module("code_environment").CodeEnvironment
    env = CodeEnvironment(session_id=str(body.get("session_id", "default")))
    if body.get("code"):
        return await env.run_python(str(body["code"]))
    r = await env.run_command(str(body.get("command", "")))
    return r.__dict__


@router.get("/code/files")
async def code_files(x_internal_key: Optional[str] = Header(None)):
    _auth(x_internal_key)
    CodeEnvironment = _platform_module("code_environment").CodeEnvironment
    return {"files": await CodeEnvironment(session_id="default").list_files()}
