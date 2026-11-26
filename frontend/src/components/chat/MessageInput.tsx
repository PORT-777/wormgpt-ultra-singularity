import { useState } from "react";
import { Pause, Send } from "lucide-react";
import { Button, Textarea } from "../PlatformUI";
export function MessageInput({ onSend, onStop, streaming }: { onSend: (s: string) => void; onStop: () => void; streaming: boolean }) {
  const [value, setValue] = useState("");
  const submit = () => { if (!value.trim()) return; onSend(value); setValue(""); };
  return <div className="flex gap-2 border-t p-3"><Textarea value={value} rows={2} placeholder="Ask anything…" onChange={e => setValue(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }} />
    <div className="flex flex-col gap-2">{streaming ? <Button variant="destructive" size="icon" onClick={onStop}><Pause size={16} /></Button> : <Button size="icon" onClick={submit}><Send size={16} /></Button>}</div></div>;
}
