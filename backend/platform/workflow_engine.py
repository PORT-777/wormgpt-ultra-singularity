"""Dify-inspired DAG workflow engine."""
from __future__ import annotations

import asyncio
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    LLM = "llm"
    RAG = "rag"
    TOOL = "tool"
    CODE = "code"
    CONDITION = "condition"
    LOOP = "loop"
    INPUT = "input"
    OUTPUT = "output"
    TRANSFORM = "transform"
    PARALLEL = "parallel"


class WorkflowNode(BaseModel):
    id: str
    type: NodeType
    config: dict[str, Any] = Field(default_factory=dict)


class WorkflowEdge(BaseModel):
    from_node: str
    to_node: str


class Workflow(BaseModel):
    id: str
    name: str = ""
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)


class WorkflowResult(BaseModel):
    outputs: dict[str, Any] = Field(default_factory=dict)
    trace: list[dict[str, Any]] = Field(default_factory=list)


def _topological(nodes: list[WorkflowNode], edges: list[WorkflowEdge]):
    indeg = {n.id: 0 for n in nodes}
    adj: dict[str, list[str]] = {n.id: [] for n in nodes}
    for e in edges:
        if e.from_node in adj and e.to_node in indeg:
            adj[e.from_node].append(e.to_node)
            indeg[e.to_node] += 1
    queue = [n for n, d in indeg.items() if d == 0]
    order = []
    while queue:
        current = queue.pop(0)
        order.append(current)
        for nxt in adj[current]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    by_id = {n.id: n for n in nodes}
    return [by_id[i] for i in order]


async def _execute_node(node: WorkflowNode, value: Any, variables: dict) -> Any:
    cfg = node.config
    if node.type == NodeType.INPUT:
        return value
    if node.type == NodeType.OUTPUT:
        return value
    if node.type == NodeType.TRANSFORM:
        template = str(cfg.get("template", "{{value}}"))
        return template.replace("{{value}}", str(value)).replace("{{input}}", str(value))
    if node.type == NodeType.RAG:
        from rag.pipeline import pipeline
        r = await pipeline.query(str(value))
        return r.answer
    if node.type == NodeType.TOOL:
        from agents.tool_registry import call_tool
        return await call_tool(str(cfg.get("tool", "")), **cfg.get("args", {}))
    if node.type == NodeType.CODE:
        from agents.sandbox import execute_python
        r = await execute_python(str(cfg.get("code", "")), timeout=10)
        return r.output or r.error
    if node.type == NodeType.CONDITION:
        return value if bool(value) else cfg.get("else", None)
    if node.type == NodeType.LOOP:
        return [await _execute_node(WorkflowNode(id="loop-body", type=NodeType.TRANSFORM,
                                                  config=cfg.get("body", {})), v, variables)
                for v in (value if isinstance(value, list) else [value])]
    if node.type == NodeType.PARALLEL:
        return await asyncio.gather(*[
            _execute_node(WorkflowNode(id=f"p{i}", type=NodeType.TRANSFORM, config=c),
                          value, variables) for i, c in enumerate(cfg.get("branches", []))])
    return value


async def execute_workflow(workflow: Workflow, trigger_input: Any = None) -> WorkflowResult:
    order = _topological(workflow.nodes, workflow.edges)
    variables = dict(workflow.variables)
    trace, outputs = [], {}
    for node in order:
        value = outputs.get(node.id, trigger_input)
        try:
            result = await _execute_node(node, value, variables)
            outputs[node.id] = result
            trace.append({"node": node.id, "type": node.type.value, "status": "ok"})
        except Exception as exc:
            outputs[node.id] = {"error": str(exc)[:300]}
            trace.append({"node": node.id, "type": node.type.value,
                          "status": "failed", "error": str(exc)[:200]})
    return WorkflowResult(outputs=outputs, trace=trace)
