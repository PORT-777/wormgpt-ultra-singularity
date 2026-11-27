import { describe, it, expect, beforeEach } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useChatStore } from "../chat.store";
describe("useChatStore", () => {
  beforeEach(() => useChatStore.setState({ messages: [], sessionId: null, mode: "chat", model: "auto", streaming: false, currentContent: "", currentSteps: [], currentSources: [] }));
  it("appends tokens", () => {
    const { result } = renderHook(() => useChatStore());
    act(() => { result.current.appendToken("Hello"); result.current.appendToken(" world"); });
    expect(result.current.currentContent).toBe("Hello world");
    expect(result.current.streaming).toBe(true);
  });
  it("finalizes", () => {
    const { result } = renderHook(() => useChatStore());
    act(() => { result.current.appendToken("answer"); result.current.finalize(150, 0.0001); });
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].content).toBe("answer");
    expect(result.current.messages[0].tokens).toBe(150);
    expect(result.current.streaming).toBe(false);
  });
  it("adds steps and sources", () => {
    const { result } = renderHook(() => useChatStore());
    act(() => {
      result.current.addStep({ agent: "researcher", content: "searching", timestamp: Date.now() });
      result.current.addSource({ id: "s1", title: "Doc A" });
      result.current.appendToken("x");
      result.current.finalize(1, 0);
    });
    expect(result.current.messages[0].sources).toHaveLength(1);
    expect(result.current.messages[0].agentSteps).toHaveLength(1);
  });
  it("resets", () => {
    const { result } = renderHook(() => useChatStore());
    act(() => { result.current.appendToken("partial"); result.current.reset(); });
    expect(result.current.messages).toHaveLength(0);
    expect(result.current.currentContent).toBe("");
  });
  it("switches mode", () => {
    const { result } = renderHook(() => useChatStore());
    act(() => result.current.setMode("rag"));
    expect(result.current.mode).toBe("rag");
  });
});
