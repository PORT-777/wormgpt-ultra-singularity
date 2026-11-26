export interface ModelInfo {
  id: string; provider: string; context: number; cost_per_1k_in: number; cost_per_1k_out: number;
  strengths: string[]; available: boolean;
}
export interface ModelCatalog { models: ModelInfo[]; }
export type RoutingStrategy = "cheapest" | "fastest" | "best_quality" | "balanced" | "task_optimal";
