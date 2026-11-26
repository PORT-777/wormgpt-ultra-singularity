import { create } from "zustand";
import type { WorkspaceInfo } from "../types/workspace.types";
interface WorkspaceState { active: WorkspaceInfo | null; setActive: (w: WorkspaceInfo | null) => void; }
export const useWorkspaceStore = create<WorkspaceState>((set) => ({ active: null, setActive: (active) => set({ active }) }));
