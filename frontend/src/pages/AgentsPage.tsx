import { useState } from "react";
import { AgentRunner } from "../components/agents/AgentRunner";
import { AgentProgress } from "../components/agents/AgentProgress";
import { ToolRegistry } from "../components/agents/ToolRegistry";
import { JobHistory } from "../components/agents/JobHistory";
import { Bot } from "lucide-react";
import { EmptyState } from "../components/PlatformUI";
export default function AgentsPage() {
  const [job, setJob] = useState<string | null>(null);
  return <div className="flex h-full"><div className="w-96 shrink-0 space-y-4 overflow-y-auto border-r p-5">
    <AgentRunner onJob={setJob} /><JobHistory onSelect={setJob} /><ToolRegistry />
  </div><div className="min-w-0 flex-1 p-6">{job ? <AgentProgress jobId={job} /> : <EmptyState icon={<Bot size={24} />} title="No active agent" description="Run an agent task to see live progress." />}</div></div>;
}
