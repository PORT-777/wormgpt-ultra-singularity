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

    client = TestClient(app)
    response = client.post(
        "/api/chat",
        json={
            "message": "scan the selected project",
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
