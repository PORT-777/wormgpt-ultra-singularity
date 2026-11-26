import { useChat } from "../../hooks/use-chat";
import { ModeSelector } from "./ModeSelector";
import { MessageBubble } from "./MessageBubble";
import { MessageInput } from "./MessageInput";
import { StreamingMessage } from "./StreamingMessage";
import { AgentSteps } from "./AgentSteps";
export function ChatWindow() {
  const chat = useChat();
  return <div className="flex min-w-0 flex-1 flex-col">
    <div className="flex items-center justify-between border-b p-3"><ModeSelector /><span className="text-xs text-muted-foreground">{chat.connected ? "Connected" : "Connecting…"}</span></div>
    <div className="flex-1 overflow-y-auto p-4">
      {!chat.messages.length && !chat.streaming && <div className="mt-20 text-center text-muted-foreground">Start a conversation.</div>}
      {chat.messages.map(m => <MessageBubble key={m.id} message={m} />)}
      {chat.streaming && <StreamingMessage content={chat.currentContent} steps={chat.currentSteps} />}
      {!!chat.currentSources.length && <AgentSteps steps={[]} />}
    </div>
    <MessageInput onSend={chat.sendMessage} onStop={chat.stop} streaming={chat.streaming} />
  </div>;
}
