import type { AgentStep } from "../../types/chat.types";
import { Loader2 } from "lucide-react";
export function AgentSteps({ steps }: { steps: AgentStep[] }) {
  return <div className="space-y-1">{steps.map((s, i) => <div key={i} className="flex items-center gap-2 text-xs text-muted-foreground">
    <Loader2 size={10} className="animate-spin" /><b className="text-primary">{s.agent}</b><span className="truncate">{s.content}</span>
  </div>)}</div>;
}
