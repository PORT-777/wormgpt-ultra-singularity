import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { RoutingStrategy } from "../types/model.types";

interface ModelState {
  selectedModel: string; strategy: RoutingStrategy; strategyBudget: number;
  setModel: (m: string) => void; setStrategy: (s: RoutingStrategy) => void; setBudget: (n: number) => void;
}
export const useModelStore = create<ModelState>()(persist((set) => ({
  selectedModel: "auto", strategy: "task_optimal", strategyBudget: 0,
  setModel: (selectedModel) => set({ selectedModel }),
  setStrategy: (strategy) => set({ strategy }),
  setBudget: (strategyBudget) => set({ strategyBudget }),
}), { name: "platform-model-prefs" }));
