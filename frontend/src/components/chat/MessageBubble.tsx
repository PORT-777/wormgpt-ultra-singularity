import { Bot, Copy, User } from "lucide-react";
import type { ChatMessage } from "../../types/chat.types";
import { MarkdownRenderer } from "../shared/MarkdownRenderer";
import { SourceCards } from "./SourceCards";
import { CostBadge } from "../shared/CostBadge";
import { Badge } from "../PlatformUI";
export function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "user") return <div className="mb-4 flex justify-end"><div className="max-w-[80%] rounded-2xl bg-primary px-4 py-2 text-sm text-primary-foreground">{message.content}</div></div>;
  return <div className="mb-4 flex gap-3">
    <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted"><Bot size={14} /></div>
    <div className="min-w-0 flex-1">
      {!!message.agentSteps?.length && <div className="mb-2 space-y-1 text-xs text-muted-foreground">{message.agentSteps.map((s, i) => <div key={i}><b className="text-primary">{s.agent}</b>: {s.content}</div>)}</div>}
      <MarkdownRenderer content={message.content} />
      {!!message.sources?.length && <SourceCards sources={message.sources} />}
      <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
        {!!message.cost && <CostBadge cost={message.cost} tokens={message.tokens} />}
        {message.model && <Badge variant="outline">{message.model}</Badge>}
        <button onClick={() => navigator.clipboard?.writeText(message.content)} className="flex items-center gap-1"><Copy size={11} /> Copy</button>
        <span>{new Date(message.timestamp).toLocaleTimeString()}</span>
      </div>
    </div>
  </div>;
}
