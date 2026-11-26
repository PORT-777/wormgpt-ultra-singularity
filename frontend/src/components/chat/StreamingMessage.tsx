import { Bot } from "lucide-react";
import { MarkdownRenderer } from "../shared/MarkdownRenderer";
import { StreamingCursor } from "../shared/StreamingCursor";
import { AgentSteps } from "./AgentSteps";
import type { AgentStep } from "../../types/chat.types";
export function StreamingMessage({ content, steps }: { content: string; steps: AgentStep[] }) {
  return <div className="mb-4 flex gap-3"><div className="mt-1 flex h-8 w-8 shrink-0 animate-pulse items-center justify-center rounded-full bg-primary/20"><Bot size={14} /></div>
    <div className="min-w-0 flex-1">{!!steps.length && <AgentSteps steps={steps} />}{content && <MarkdownRenderer content={content} />}<StreamingCursor /></div></div>;
}
