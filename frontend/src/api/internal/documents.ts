import { apiPost } from "../client";
export const parseDocument = (source: string, mime = "text/plain") =>
  apiPost<Record<string, unknown>>("/api/internal/docs/parse", { source, mime_type: mime });
export const classifyDocument = (text: string) =>
  apiPost<Record<string, unknown>>("/api/internal/docs/classify", { text });
export const summarizeDocument = (text: string) =>
  apiPost<Record<string, unknown>>("/api/internal/docs/summarize", { text });
