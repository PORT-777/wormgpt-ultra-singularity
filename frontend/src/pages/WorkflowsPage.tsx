import { useState } from "react";
import { WorkflowList } from "../components/workflow/WorkflowList";
import { WorkflowBuilder } from "../components/workflow/WorkflowBuilder";
import { Workflow } from "lucide-react";
import { EmptyState, Button } from "../components/PlatformUI";
export default function WorkflowsPage() {
  const [id, setId] = useState<string | null>(null);
  return <div className="flex h-full"><div className="w-64 shrink-0 space-y-3 border-r p-4">
    <div className="flex items-center justify-between"><h2 className="font-semibold">Workflows</h2><Button size="sm" onClick={() => setId("new")}>+ New</Button></div>
    <WorkflowList onSelect={setId} /></div><div className="min-w-0 flex-1 p-4">{id ? <WorkflowBuilder /> : <EmptyState icon={<Workflow size={24} />} title="No workflow selected" description="Create or select a workflow to edit its DAG." />}</div></div>;
}
