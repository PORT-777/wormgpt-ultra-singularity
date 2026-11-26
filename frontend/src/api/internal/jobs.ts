import { apiGet, apiPost } from "../client";
export const submitJob = (taskType: string, payload: Record<string, unknown>) =>
  apiPost<{ job_id: string }>("/api/internal/jobs/submit", { task_type: taskType, payload });
export const jobResult = (id: string) => apiGet<Record<string, unknown>>(`/api/internal/jobs/${id}/result`);
