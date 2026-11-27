import { WS_BASE } from "../../lib/constants";

export type WSMessage = Record<string, unknown> & { type?: string };

export class WSClient {
  private ws: WebSocket | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private disposed = false;
  constructor(private sessionId: string, private base: string = WS_BASE) {}
  connect(handlers: { onMessage?: (m: WSMessage) => void; onOpen?: () => void; onClose?: () => void }) {
    const open = () => {
      this.ws = new WebSocket(`${this.base}/ws/chat/${encodeURIComponent(this.sessionId)}`);
      this.ws.onopen = () => handlers.onOpen?.();
      this.ws.onmessage = (e) => {
        try { handlers.onMessage?.(JSON.parse(e.data) as WSMessage); } catch { /* ignore */ }
      };
      this.ws.onclose = () => {
        handlers.onClose?.();
        if (!this.disposed) this.timer = setTimeout(open, 2000);
      };
    };
    open();
  }
  send(msg: WSMessage) {
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(msg));
  }
  close() {
    this.disposed = true;
    if (this.timer) clearTimeout(this.timer);
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.close();
      this.ws = null;
    }
  }
}
