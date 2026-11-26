import { create } from "zustand";
interface UIState { sidebarOpen: boolean; rightPanelOpen: boolean; toggleSidebar: () => void; setRightPanel: (v: boolean) => void; }
export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true, rightPanelOpen: false,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setRightPanel: (rightPanelOpen) => set({ rightPanelOpen }),
}));
