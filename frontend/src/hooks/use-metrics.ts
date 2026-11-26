import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../lib/query-keys";
import { getMetrics } from "../api/internal/eval";
export function useMetrics(period = "24h") {
  return useQuery({ queryKey: queryKeys.metrics.platform(period), queryFn: () => getMetrics(period), refetchInterval: 30_000 });
}
