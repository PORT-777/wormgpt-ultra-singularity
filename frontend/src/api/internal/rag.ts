import { apiGet, apiPost } from "../client";
export const ragQuery = (question: string, top_k = 5) =>
  apiPost<Record<string, unknown>>("/api/internal/rag/query", { question, top_k });
export const ragIngest = (source: string, metadata: Record<string, unknown> = {}) =>
  apiPost<Record<string, unknown>>("/api/internal/rag/ingest", { source, metadata });
export const ragDocuments = () => apiGet<{ documents: unknown[] }>("/api/internal/rag/documents");
export const ragStats = () => apiGet<Record<string, unknown>>("/api/internal/rag/stats");
export const ragSearch = (question: string) => apiPost<Record<string, unknown>>("/api/internal/rag/search", { question });
