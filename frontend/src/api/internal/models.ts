import { apiGet, apiPost } from "../client";
import type { ModelCatalog, RoutingStrategy } from "../../types/model.types";

export const getModelCatalog = () => apiGet<ModelCatalog>("/api/internal/models/catalog");
export const getModelUsage = () => apiGet<Record<string, unknown>>("/api/internal/models/usage");
export const getModelCost = () => apiGet<Record<string, unknown>>("/api/internal/models/cost");
export const routeModel = (prompt: string, strategy: RoutingStrategy) =>
  apiPost<Record<string, unknown>>("/api/internal/models/route", { prompt, strategy });
export const callAuto = (prompt: string) => apiPost<Record<string, unknown>>("/api/internal/models/call/auto", { prompt });
export const cacheQuery = (prompt: string) => apiPost<Record<string, unknown>>("/api/internal/models/cache/query", { prompt });
