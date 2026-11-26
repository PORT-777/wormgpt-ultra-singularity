import { useCallback, useEffect, useRef } from "react";
import type { SSEEvent } from "../api/streaming/sse-client";
import { SSEClient } from "../api/streaming/sse-client";

export interface SSEHandlers {
  onToken?: (c: string) => void; onStep?: (c: string, a: string) => void;
  onSource?: (url: string, title: string) => void; onDone?: (t: number, c: number) => void;
  onError?: (m: string) => void;
}
export function useSSE(sessionId: string | null, handlers: SSEHandlers) {
  const ref = useRef<SSEClient | null>(null);
  const connect = useCallback(() => {
    if (!sessionId) return;
    const client = new SSEClient(sessionId);
    ref.current = client;
    client.connect({
      onEvent: (e: SSEEvent) => {
        switch (e.type) {
          case "token": handlers.onToken?.(String(e.content ?? "")); break;
          case "step": handlers.onStep?.(String(e.content ?? ""), String(e.agent ?? "agent")); break;
          case "source": handlers.onSource?.(String(e.url ?? ""), String(e.title ?? "")); break;
          case "done": handlers.onDone?.(Number(e.tokens ?? 0), Number(e.cost ?? 0)); break;
          case "error": handlers.onError?.(String(e.message ?? "error")); break;
        }
      },
      onError: handlers.onError,
    });
  }, [sessionId]);
  useEffect(() => { connect(); return () => ref.current?.close(); }, [connect]);
  return { disconnect: () => ref.current?.close() };
}
