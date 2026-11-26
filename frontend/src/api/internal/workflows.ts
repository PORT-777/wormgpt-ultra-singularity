import { apiPost } from "../client";
export const runWorkflow = (workflow: Record<string, unknown>, trigger: unknown = null) =>
  apiPost<Record<string, unknown>>("/api/internal/workflows/run", { workflow, trigger_input: trigger });
