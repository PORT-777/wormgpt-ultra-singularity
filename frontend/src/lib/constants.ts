export const API_BASE: string = import.meta.env.VITE_API_BASE ?? "http://localhost:7777";
export const WS_BASE: string = import.meta.env.VITE_WS_BASE ?? "ws://localhost:7777";
export const INTERNAL_KEY: string = import.meta.env.VITE_INTERNAL_API_KEY ?? "";
export const APP_NAME: string = import.meta.env.VITE_APP_NAME ?? "AI Platform";

export const ROUTES = {
  chat: "/", dashboard: "/dashboard", workspaces: "/workspaces",
  models: "/models", agents: "/agents", workflows: "/workflows",
  traces: "/traces", settings: "/settings",
} as const;
