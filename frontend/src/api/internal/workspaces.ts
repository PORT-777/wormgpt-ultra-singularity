import { apiGet, apiPost } from "../client";
import type { WorkspaceInfo } from "../../types/workspace.types";
export const listWorkspaces = () => apiGet<{ workspaces: WorkspaceInfo[] }>("/api/internal/workspaces");
export const createWorkspace = (name: string) => apiPost<WorkspaceInfo>("/api/internal/workspaces", { name });
export const workspaceChat = (id: string, question: string) =>
  apiPost<Record<string, unknown>>(`/api/internal/workspaces/${id}/chat`, { question });
