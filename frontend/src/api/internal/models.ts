import { apiGet, apiPost } from "../client";
import type { ModelCatalog, ModelInfo, RoutingStrategy } from "../../types/model.types";

interface RawCatalog { models?: Record<string, Omit<ModelInfo, "id">> | ModelInfo[] }

function normalizeCatalog(raw: RawCatalog): ModelCatalog {
  const value = raw.models ?? {};
  const models: ModelInfo[] = Array.isArray(value)
    ? value
    : Object.entries(value).map(([id, spec]) => ({ id, ...spec }));
  return { models };
}

export async function getModelCatalog(): Promise<ModelCatalog> {
  const raw = await apiGet<RawCatalog>("/api/internal/models/catalog");
  return normalizeCatalog(raw);
}
export const getModelUsage = () => apiGet<Record<string, unknown>>("/api/internal/models/usage");
export const getModelCost = () => apiGet<Record<string, unknown>>("/api/internal/models/cost");
export const routeModel = (prompt: string, strategy: RoutingStrategy) =>
  apiPost<Record<string, unknown>>("/api/internal/models/route", { prompt, strategy });
export const callAuto = (prompt: string) => apiPost<Record<string, unknown>>("/api/internal/models/call/auto", { prompt });
export const cacheQuery = (prompt: string) => apiPost<Record<string, unknown>>("/api/internal/models/cache/query", { prompt });
