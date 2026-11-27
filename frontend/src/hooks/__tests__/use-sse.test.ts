import { describe, it, expect, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSSE } from "../use-sse";

class MockEventSource {
  static CONNECTING = 0; static OPEN = 1; static CLOSED = 2;
  static instances: MockEventSource[] = [];
  readyState = 1;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
  constructor() { MockEventSource.instances.push(this); }
  emit(data: unknown) { this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent); }
  done() { this.onmessage?.({ data: "[DONE]" } as MessageEvent); }
}
vi.stubGlobal("EventSource", MockEventSource);
const last = () => MockEventSource.instances[MockEventSource.instances.length - 1];

describe("useSSE", () => {
  it("token", () => {
    const onToken = vi.fn(); renderHook(() => useSSE("s1", { onToken }));
    act(() => last().emit({ type: "token", content: "Hello" }));
    expect(onToken).toHaveBeenCalledWith("Hello");
  });
  it("done", () => {
    const onDone = vi.fn(); renderHook(() => useSSE("s1", { onDone }));
    act(() => last().emit({ type: "done", tokens: 100, cost: 0.001 }));
    expect(onDone).toHaveBeenCalledWith(100, 0.001);
  });
  it("closes on DONE", () => {
    renderHook(() => useSSE("s1", {}));
    const es = last(); act(() => es.done());
    expect(es.close).toHaveBeenCalled();
  });
  it("source", () => {
    const onSource = vi.fn(); renderHook(() => useSSE("s1", { onSource }));
    act(() => last().emit({ type: "source", url: "https://e.com", title: "E" }));
    expect(onSource).toHaveBeenCalledWith("https://e.com", "E");
  });
  it("no session no connect", () => {
    const n = MockEventSource.instances.length;
    renderHook(() => useSSE(null, {}));
    expect(MockEventSource.instances.length).toBe(n);
  });
});
