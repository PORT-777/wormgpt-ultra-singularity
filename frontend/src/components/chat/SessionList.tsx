import { Plus } from "lucide-react";
import { Button } from "../PlatformUI";
import { useChatStore } from "../../store/chat.store";
export function SessionList() {
  const { sessionId, setSessionId, clear } = useChatStore();
  return <div className="hidden w-56 shrink-0 flex-col border-r p-3 lg:flex">
    <Button size="sm" className="mb-3" onClick={() => { setSessionId(crypto.randomUUID()); clear(); }}><Plus size={13} /> New chat</Button>
    <div className="text-xs text-muted-foreground">{sessionId ? `Session ${sessionId.slice(0, 8)}` : "No active session"}</div>
  </div>;
}
