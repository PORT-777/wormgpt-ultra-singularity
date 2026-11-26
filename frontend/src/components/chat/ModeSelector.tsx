import { Bot, Database, MessageSquare } from "lucide-react";
import { useChatStore } from "../../store/chat.store";
import type { ChatMode } from "../../types/chat.types";
import { cn } from "../../lib/utils";
const MODES: { id: ChatMode; label: string; icon: typeof MessageSquare; desc: string }[] = [
  { id: "chat", label: "Chat", icon: MessageSquare, desc: "Direct conversation" },
  { id: "rag", label: "Knowledge", icon: Database, desc: "Answers from your documents" },
  { id: "agent", label: "Agent", icon: Bot, desc: "Multi-step tools and reasoning" },
];
export function ModeSelector() {
  const { mode, setMode } = useChatStore();
  return <div className="flex gap-1 rounded-lg border bg-muted/40 p-1">{MODES.map(m => <button key={m.id} title={m.desc} onClick={() => setMode(m.id)}
    className={cn("flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs", mode === m.id ? "bg-background shadow" : "text-muted-foreground")}>
    <m.icon size={13} />{m.label}</button>)}</div>;
}
