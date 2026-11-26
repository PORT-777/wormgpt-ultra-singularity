import { create } from "zustand";
interface SessionState { activeId: string | null; setActive: (id: string) => void; }
export const useSessionStore = create<SessionState>((set) => ({ activeId: null, setActive: (activeId) => set({ activeId }) }));
