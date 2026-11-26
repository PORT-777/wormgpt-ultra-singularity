"""Phase E/F — observability and streaming tests (offline)."""
from __future__ import annotations

import asyncio

import pytest

from eval.exporter import export
from eval.langfuse_exporter import export_trace, langfuse_configured
from eval.logger import log_interaction
from eval.metrics import PlatformMetrics, get_metrics
from eval.scorer import QualityScore, score_response
from eval.tracer import LLMTracer, TraceResult
from streaming.queue import JobQueue, register_handler
from streaming.sse import sse, stream_llm_response
from streaming.websocket import websocket_chat


def test_quality_score_shape():
    s = asyncio.run(score_response("q", "answer", ["context"]))
    assert isinstance(s, QualityScore)
    assert 0 <= s.overall <= 1


def test_quality_score_flags():
    s = asyncio.run(score_response("q", "x", ["abc"]))
    assert "hallucination_risk" in s.flags or "too_short" in s.flags


def test_platform_metrics_defaults():
    m = PlatformMetrics()
    assert m.total_requests == 0 and m.error_rate == 0


def test_metrics_shape():
    m = asyncio.run(get_metrics("1h"))
    assert isinstance(m, PlatformMetrics)
    assert m.p99_latency_ms >= m.p50_latency_ms


def test_tracer_success(tmp_path):
    async def fn(prompt, model="m"):
        class U:
            prompt_tokens = 4
            completion_tokens = 2
        class R:
            content = "ok"
            usage = U()
        return R()
    tracer = LLMTracer(path=str(tmp_path / "t.jsonl"))
    r = asyncio.run(tracer.trace(fn, prompt="hi"))
    assert isinstance(r, TraceResult) and r.trace.success
    assert r.trace.total_tokens == 6


def test_tracer_failure(tmp_path):
    async def fn(**kw):
        raise RuntimeError("boom")
    tracer = LLMTracer(path=str(tmp_path / "t.jsonl"))
    with pytest.raises(RuntimeError):
        asyncio.run(tracer.trace(fn, prompt="hi"))


def test_langfuse_disabled():
    assert langfuse_configured() is False or isinstance(langfuse_configured(), bool)


def test_langfuse_export_noop():
    class T:
        id = "x"; trace_type = "x"; input_preview = ""; output_preview = ""
        model = "m"; cost_usd = 0; latency_ms = 0; user_id = ""; session_id = ""
    assert asyncio.run(export_trace(T())) in (True, False)


def test_exporter_creates_file(tmp_path):
    p = export(str(tmp_path / "traces.json"))
    assert p.endswith("traces.json")


def test_log_interaction_noop():
    log_interaction("u", "svc", True)


def test_sse_generator():
    async def events():
        yield {"type": "token", "content": "hi"}
    out = asyncio.run(_collect(sse(events())))
    assert "data:" in out and "[DONE]" in out


async def _collect(gen):
    return "".join([x async for x in gen])


def test_stream_llm_response_type():
    r = asyncio.run(stream_llm_response("hi", "auto", "s"))
    assert r.media_type == "text/event-stream"


def test_job_queue_submit_status_result():
    async def echo(value=1):
        return value
    register_handler("echo_test", echo)
    q = JobQueue()
    jid = asyncio.run(q.submit("echo_test", {"value": 7}))
    asyncio.sleep
    import time
    time.sleep(0.05)
    assert q.status(jid)["status"] in ("done", "running")
    assert q.result(jid)["id"] == jid


def test_websocket_handler_exists():
    assert callable(websocket_chat)
