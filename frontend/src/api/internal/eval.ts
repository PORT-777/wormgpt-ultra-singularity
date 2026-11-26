import { apiGet, apiPost } from "../client";
export const getMetrics = (period = "24h") => apiGet<Record<string, unknown>>(`/api/internal/eval/metrics?period=${period}`);
export const getTraces = (limit = 50) => apiGet<{ traces: unknown[] }>(`/api/internal/eval/traces?limit=${limit}`);
export const scoreResponse = (question: string, response: string, context: string[] = []) =>
  apiPost<Record<string, unknown>>("/api/internal/eval/score", { question, response, context });
export const getHealth = () => apiGet<Record<string, unknown>>("/api/internal/eval/health/all");
export const getProjection = () => apiGet<Record<string, unknown>>("/api/internal/eval/cost/projection");
