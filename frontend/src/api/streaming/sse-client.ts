import { API_BASE, INTERNAL_KEY } from "../../lib/constants";

export type SSEEvent = Record<string, unknown> & { type?: string };

export class SSEClient {
  private source: EventSource | null = null;
  constructor(private sessionId: string, private base: string = API_BASE) {}
  connect(handlers: {
    onEvent?: (e: SSEEvent) => void; onDone?: () => void; onError?: (msg: string) => void;
  }) {
    const url = `${this.base}/api/internal/stream/sse/${encodeURIComponent(this.sessionId)}?key=${encodeURIComponent(INTERNAL_KEY)}`;
    this.source = new EventSource(url);
    this.source.onmessage = (e) => {
      if (e.data === "[DONE]") { handlers.onDone?.(); this.close(); return; }
      try { handlers.onEvent?.(JSON.parse(e.data) as SSEEvent); } catch { /* ignore */ }
    };
    this.source.onerror = () => handlers.onError?.("Stream interrupted, reconnecting…");
  }
  close() { this.source?.close(); this.source = null; }
}
