import { useMutation } from "@tanstack/react-query";
import { ragQuery } from "../api/internal/rag";
export function useRAG() {
  return useMutation({ mutationFn: (q: string) => ragQuery(q) });
}
