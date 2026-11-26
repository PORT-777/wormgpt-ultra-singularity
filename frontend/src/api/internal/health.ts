import { apiGet } from "../client";
import type { HealthDashboard } from "../../types/api.types";
export const healthAll = () => apiGet<HealthDashboard>("/api/internal/health/all");
