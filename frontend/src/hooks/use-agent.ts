import { useMutation } from "@tanstack/react-query";
import { runAgent } from "../api/internal/agents";
export function useAgent() {
  return useMutation({ mutationFn: (task: string) => runAgent(task) });
}
