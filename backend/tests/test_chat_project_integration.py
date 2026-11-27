"""End-to-end chat path test: project selection -> real tool execution in chat."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import agent_engine  # noqa: E402
from conftest import FakeBrain  # noqa: E402
from tools.intelligence_tool import CodeIntelligence  # noqa: E402


def test_chat_executes_code_intelligence_for_selected_project(tmp_path, monkeypatch):
    (tmp_path / "app.py").write_text("def add(a,b):\n    return a+b\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# sample\n", encoding="utf-8")

    calls = []
    original_run = CodeIntelligence.run

    async def recording_run(self, **kwargs):
        calls.append(kwargs)
        return await original_run(self, **kwargs)

    monkeypatch.setattr(CodeIntelligence, "run", recording_run)
    monkeypatch.setattr(agent_engine.config, "MEMORY_ENABLED", False)

    brain = FakeBrain([
        'Thought: scan the selected project\nAction: CodeIntelligence\n'
        'Action Input: {"action": "scan_project", "path": "' + str(tmp_path).replace("\\", "/") + '"}',
        'Thought: done\nFinal Answer: project scanned',
    ])
    monkeypatch.setattr(agent_engine, "ENGINE", agent_engine.AgentEngine())

    # Force the scripted brain on the singleton the endpoint imports.
    engine = agent_engine.AgentEngine()
    monkeypatch.setattr(agent_engine, "ENGINE", engine)
    monkeypatch.setattr(
        agent_engine.ROUTER, "resolve", lambda *a, **k: ("test", brain)
    )

    from backend.main import app

    sid = "itest-session-001"
    client = TestClient(app)
    response = client.post(
        "/api/chat",
        json={
            "message": "scan the selected project",
            "session_id": sid,
            "project_path": str(tmp_path),
            "stream": False,
            "model": "auto",
        },
    )
    assert response.status_code == 200, response.text[:300]
    body = response.json()
    assert body["status"] == "ok"
    assert body["project_path"] == str(tmp_path)
    assert calls, "CodeIntelligence was not executed from the chat endpoint"
    assert calls[0]["action"] == "scan_project"

    import storage

    rows = storage.get_history(sid, limit=10)
    assert any(r["role"] == "user" and "scan the selected" in r["content"] for r in rows)
    assert any(r["role"] == "assistant" and r["content"] for r in rows)


def test_history_endpoints_expose_persisted_session(monkeypatch):
    """GET /api/history and /api/history/<sid>/detail must see the persisted chat turn."""
    # The endpoint imports ENGINE from backend.agent_engine (module A); the
    # top-level `agent_engine` import is a separate module object, so patch A.
    from backend import agent_engine as backend_agent_engine

    monkeypatch.setattr(backend_agent_engine.config, "MEMORY_ENABLED", False)
    brain = FakeBrain(["Thought: greeting\nFinal Answer: hello from the engine"])
    engine = backend_agent_engine.AgentEngine()
    monkeypatch.setattr(backend_agent_engine, "ENGINE", engine)
    monkeypatch.setattr(
        backend_agent_engine.ROUTER, "resolve", lambda *a, **k: ("test", brain)
    )

    from backend.main import app

    sid = "itest-history-001"
    client = TestClient(app)
    response = client.post(
        "/api/chat",
        json={
            "message": "hello from history test",
            "session_id": sid,
            "stream": False,
            "model": "auto",
        },
    )
    assert response.status_code == 200, response.text[:300]
    assert response.json()["status"] == "ok"

    # Session list endpoint shows the session with the user-titled subject.
    listing = client.get("/api/history")
    assert listing.status_code == 200, listing.text[:300]
    sessions = listing.json()
    assert isinstance(sessions, list)
    assert any(s.get("id") == sid for s in sessions), f"session {sid} missing from /api/history"

    # Full session detail includes both persisted turns.
    detail = client.get(f"/api/history/{sid}")
    assert detail.status_code == 200, detail.text[:300]
    row = detail.json()
    assert row.get("id") == sid
    roles_contents = [(m.get("role"), m.get("content", "")) for m in row.get("messages", [])]
    assert any(r == "user" and "hello from history test" in c for r, c in roles_contents)
    assert any(r == "assistant" and "hello from the engine" in c for r, c in roles_contents)

    # Messages-only detail endpoint mirrors the same persisted rows.
    msgs = client.get(f"/api/history/{sid}/detail")
    assert msgs.status_code == 200, msgs.text[:300]
    msg_rows = msgs.json()
    assert isinstance(msg_rows, list) and msg_rows, "empty /api/history/<sid>/detail"
    assert any(m.get("role") == "user" and "hello from history test" in m.get("content", "") for m in msg_rows)
    assert any(m.get("role") == "assistant" for m in msg_rows)

    # Unknown session: detail 404s; the messages-only endpoint returns 200 + [].
    assert client.get("/api/history/does-not-exist").status_code == 404
    empty = client.get("/api/history/does-not-exist/detail")
    assert empty.status_code == 200 and empty.json() == []


def test_midstream_failure_emits_error_event_and_persists_error_line(monkeypatch):
    """A mid-stream crash must emit an SSE error event AND persist an [error] line."""
    from backend import agent_engine as backend_agent_engine

    monkeypatch.setattr(backend_agent_engine.config, "MEMORY_ENABLED", False)
    engine = backend_agent_engine.ENGINE or backend_agent_engine.AgentEngine()
    monkeypatch.setattr(backend_agent_engine, "ENGINE", engine)

    async def failing_run_stream(*args, **kwargs):
        yield {"type": "stream", "data": "partial before failure"}
        raise RuntimeError("boom mid-stream")

    monkeypatch.setattr(engine, "run_stream", failing_run_stream)

    from backend.main import app

    sid = "itest-error-001"
    client = TestClient(app)
    response = client.post(
        "/api/chat",
        json={
            "message": "cause a failure",
            "session_id": sid,
            "stream": True,
            "model": "auto",
        },
    )
    assert response.status_code == 200, response.text[:300]
    assert "boom mid-stream" in response.text, "error event was not streamed"

    import storage

    rows = storage.get_history(sid, limit=10)
    assert any(
        r["role"] == "error" and r["content"].startswith("[error]")
        and "boom mid-stream" in r["content"]
        for r in rows
    ), "no [error] line persisted for the failed turn"
