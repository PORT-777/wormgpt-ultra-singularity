import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../lib/query-keys";
import { getModelCatalog } from "../api/internal/models";
export function useModels() {
  return useQuery({ queryKey: queryKeys.models.catalog, queryFn: getModelCatalog, staleTime: 300_000 });
}
