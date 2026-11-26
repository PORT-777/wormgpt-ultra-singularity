import { useCallback, useState } from "react";
import { ReactFlow, addEdge, Background, Controls, MiniMap, Panel, useEdgesState, useNodesState } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { apiClient } from "../../api/client";
import { Button } from "../PlatformUI";
import { Play, Plus } from "lucide-react";
const TYPES = ["input","llm","rag","tool","condition","output"];
export function WorkflowBuilder() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [running, setRunning] = useState(false);
  const onConnect = useCallback((p: Parameters<typeof addEdge>[0]) => setEdges(e => addEdge(p, e)), [setEdges]);
  const addNode = (type: string) => setNodes(n => [...n, { id: `${type}-${Date.now()}`, type: "default", position: { x: Math.random()*400, y: Math.random()*250 }, data: { label: type, type } }]);
  const run = async () => { setRunning(true); try {
    await apiClient.post("/api/internal/jobs/submit", { task_type: "workflow", payload: { workflow: { id: "ui", name: "UI workflow", nodes: nodes.map(n => ({ id: n.id, type: n.data.type, config: {} })), edges: edges.map(e => ({ from_node: e.source, to_node: e.target })) }, input: "Start" } });
  } finally { setRunning(false); } };
  return <div className="h-[70vh]"><ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect} fitView>
    <Background /><Controls /><MiniMap />
    <Panel position="top-left" className="flex flex-wrap gap-1">{TYPES.map(t => <Button key={t} size="sm" variant="outline" onClick={() => addNode(t)}><Plus size={12} />{t}</Button>)}</Panel>
    <Panel position="top-right"><Button size="sm" onClick={run} disabled={running}>{running ? "…" : <><Play size={12} /> Run</>}</Button></Panel>
  </ReactFlow></div>;
}
