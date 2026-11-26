import { apiGet, apiPost } from "../client";
export const runAgent = (task: string, agent = "") =>
  apiPost<Record<string, unknown>>("/api/internal/agents/run", { task, agent });
export const runNamedAgent = (name: string, task: string) =>
  apiPost<Record<string, unknown>>(`/api/internal/agents/${name}/run`, { task });
export const getTools = () => apiGet<{ tools: unknown[] }>("/api/internal/agents/tools");
export const jobStatus = (id: string) => apiGet<Record<string, unknown>>(`/api/internal/agents/jobs/${id}`);
