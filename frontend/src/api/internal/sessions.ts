import { apiGet, apiPost } from "../client";
export const createSession = (userId = "default", model = "auto") =>
  apiPost<Record<string, unknown>>("/api/internal/sessions", { user_id: userId, model });
export const getSession = (id: string) => apiGet<Record<string, unknown>>(`/api/internal/sessions/${id}`);
