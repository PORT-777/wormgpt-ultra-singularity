import { useCallback, useEffect, useRef, useState } from "react";
import { WSClient, type WSMessage } from "../api/streaming/ws-client";

export function useWebSocket(sessionId: string | null, onMessage: (m: WSMessage) => void) {
  const ref = useRef<WSClient | null>(null);
  const [connected, setConnected] = useState(false);
  const handlerRef = useRef(onMessage);
  handlerRef.current = onMessage;
  useEffect(() => {
    if (!sessionId) return;
    const client = new WSClient(sessionId);
    ref.current = client;
    client.connect({
      onMessage: (m) => handlerRef.current(m),
      onOpen: () => setConnected(true),
      onClose: () => setConnected(false),
    });
    return () => client.close();
  }, [sessionId]);
  const send = useCallback((msg: WSMessage) => ref.current?.send(msg), []);
  return { send, connected };
}
