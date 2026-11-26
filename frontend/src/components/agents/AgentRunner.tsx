import { useState } from "react";
import { useAgent } from "../../hooks/use-agent";
import { Button, Textarea, ErrorState } from "../PlatformUI";
const AGENTS = ["", "researcher", "coder", "analyst", "writer", "moderator"];
export function AgentRunner({ onJob }: { onJob?: (id: string) => void }) {
  const [task, setTask] = useState("");
  const [agent, setAgent] = useState("");
  const m = useAgent();
  const run = () => m.mutate(task, { onSuccess: (r) => onJob?.(String(r.id ?? r.answer ?? "")) });
  return <div className="space-y-2"><Textarea rows={3} value={task} onChange={e => setTask(e.target.value)} placeholder="Describe an agent task…" />
    <select value={agent} onChange={e => setAgent(e.target.value)} className="w-full rounded-md border bg-background p-2 text-xs">{AGENTS.map(a => <option key={a} value={a}>{a || "auto-route"}</option>)}</select>
    <Button className="w-full" disabled={!task.trim() || m.isPending} onClick={run}>{m.isPending ? "Running…" : "Run agent"}</Button>
    {m.isError && <ErrorState message={String(m.error)} />}</div>;
}
