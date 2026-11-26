import { useCallback } from "react";
import { useChatStore } from "../store/chat.store";
import { useWebSocket } from "./use-websocket";

export function useChat() {
  const store = useChatStore();
  const { send, connected } = useWebSocket(store.sessionId, (msg) => {
    switch (msg.type) {
      case "token": store.appendToken(String(msg.content ?? "")); break;
      case "step": store.addStep({ agent: String(msg.agent ?? "agent"), content: String(msg.content ?? ""), timestamp: Date.now() }); break;
      case "source": store.addSource({ id: crypto.randomUUID(), title: String(msg.title ?? ""), url: String(msg.url ?? "") }); break;
      case "done": store.finalize(Number(msg.tokens ?? 0), Number(msg.cost ?? 0)); break;
      case "error": store.reset(); break;
    }
  });
  const sendMessage = useCallback((content: string) => {
    store.addMessage({ id: crypto.randomUUID(), role: "user", content, timestamp: Date.now() });
    send({ type: "message", content, mode: store.mode });
  }, [send, store]);
  const stop = useCallback(() => send({ type: "interrupt" }), [send]);
  return { ...store, sendMessage, stop, connected };
}
