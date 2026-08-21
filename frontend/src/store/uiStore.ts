import { create } from "zustand";

export type SseStatus = "connecting" | "connected" | "disconnected";

interface UIState {
  sidebarCollapsed: boolean;
  sseStatus: SseStatus;
  /** Convenience mirror of sseStatus === "connected". */
  sseConnected: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setSseStatus: (status: SseStatus) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  sseStatus: "connecting",
  sseConnected: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),
  setSseStatus: (sseStatus) => set({ sseStatus, sseConnected: sseStatus === "connected" }),
}));
