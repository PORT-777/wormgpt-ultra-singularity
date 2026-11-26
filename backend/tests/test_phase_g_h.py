"""Phase G/H — platform patterns and route surface tests."""
from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

import external_apis.config as ext_config
from platform.chat_session import ChatMode, ChatSession, create_session, get_session, list_sessions
from platform.code_environment import CodeEnvironment, CommandResult
from platform.workflow_engine import (NodeType, Workflow, WorkflowEdge, WorkflowNode,
                                      WorkflowResult, execute_workflow)
from platform.workspace import Workspace, chat, create_workspace, get_workspace, list_workspaces


def test_chat_session_model():
    s = ChatSession(user_id="u")
    assert s.id and s.mode == ChatMode.CHAT


def test_session_create_get_list():
    s = create_session("u1")
    assert get_session(s.id) is s
    assert any(x.id == s.id for x in list_sessions("u1"))


def test_session_switch_model():
    s = ChatSession(model="a")
    s.switch_model("b")
    assert s.model == "b" and s.previous_model == "a"


def test_workspace_model():
    ws = Workspace(name="x")
    assert ws.vector_collection.startswith("ws_")


def test_workspace_crud():
    ws = create_workspace("probe")
    assert get_workspace(ws.id) is ws
    assert any(x.id == ws.id for x in list_workspaces())


def test_workspace_chat_missing():
    assert "error" in asyncio.run(chat("missing", "hi"))


def test_workflow_topological_order():
    wf = Workflow(id="w", nodes=[
        WorkflowNode(id="a", type=NodeType.INPUT),
        WorkflowNode(id="b", type=NodeType.TRANSFORM, config={"template": "v={{value}}"}),
    ], edges=[WorkflowEdge(from_node="a", to_node="b")])
    r = asyncio.run(execute_workflow(wf, "hello"))
    assert isinstance(r, WorkflowResult)
    assert r.outputs["b"] == "v=hello"


def test_workflow_condition():
    wf = Workflow(id="w", nodes=[WorkflowNode(id="a", type=NodeType.CONDITION,
                                               config={"else": "no"})])
    r = asyncio.run(execute_workflow(wf, True))
    assert r.outputs["a"] is True


def test_code_environment_sandbox_path():
    env = CodeEnvironment(session_id="probe")
    try:
        env._resolve("../../etc/passwd")
        assert False
    except ValueError:
        assert True


def test_code_environment_write_read(tmp_path):
    env = CodeEnvironment(base=str(tmp_path), session_id="probe")
    p = asyncio.run(env.write_file("a.txt", "hello"))
    assert asyncio.run(env.read_file("a.txt")) == "hello"


def test_code_environment_command_whitelist():
    env = CodeEnvironment(session_id="probe")
    r = asyncio.run(env.run_command("rm -rf /"))
    assert isinstance(r, CommandResult) and r.exit_code == -1


def test_main_openapi_routes():
    from api.internal_platform import router
    paths = {route.path for route in router.routes}
    assert "/api/internal/rag/query" in paths
    assert "/api/internal/models/catalog" in paths
    assert "/api/internal/agents/run" in paths


def test_internal_routes_fail_closed(monkeypatch):
    from api.internal_platform import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    monkeypatch.setattr(ext_config, "internal_key", "")
    client = TestClient(app)
    assert client.post("/api/internal/rag/query", json={"question": "x"}).status_code == 503
    monkeypatch.setattr(ext_config, "internal_key", "k")
    assert client.post("/api/internal/rag/query", json={"question": "x"},
                       headers={"x-internal-key": "k"}).status_code == 200
