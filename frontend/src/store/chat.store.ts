import { create } from "zustand";
import type { AgentStep, ChatMessage, ChatMode, Source } from "../types/chat.types";

interface ChatState {
  messages: ChatMessage[]; sessionId: string | null; mode: ChatMode; model: string;
  streaming: boolean; currentContent: string; currentSteps: AgentStep[]; currentSources: Source[];
  setSessionId: (id: string) => void; setMode: (m: ChatMode) => void; setModel: (m: string) => void;
  addMessage: (m: ChatMessage) => void; appendToken: (t: string) => void;
  addStep: (s: AgentStep) => void; addSource: (s: Source) => void;
  finalize: (tokens?: number, cost?: number) => void; reset: () => void; clear: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [], sessionId: null, mode: "chat", model: "auto/free",
  streaming: false, currentContent: "", currentSteps: [], currentSources: [],
  setSessionId: (sessionId) => set({ sessionId }),
  setMode: (mode) => set({ mode }),
  setModel: (model) => set({ model }),
  addMessage: (m) => set((s) => ({ messages: [...s.messages, m] })),
  appendToken: (t) => set((s) => ({ streaming: true, currentContent: s.currentContent + t })),
  addStep: (step) => set((s) => ({ currentSteps: [...s.currentSteps, step] })),
  addSource: (source) => set((s) => ({ currentSources: [...s.currentSources, source] })),
  finalize: (tokens = 0, cost = 0) => set((s) => ({
    messages: [...s.messages, {
      id: crypto.randomUUID(), role: "assistant", content: s.currentContent,
      model: s.model, tokens, cost, sources: [...s.currentSources],
      agentSteps: [...s.currentSteps], timestamp: Date.now(),
    }],
    streaming: false, currentContent: "", currentSteps: [], currentSources: [],
  })),
  reset: () => set({ streaming: false, currentContent: "", currentSteps: [], currentSources: [] }),
  clear: () => set({ messages: [] }),
}));
