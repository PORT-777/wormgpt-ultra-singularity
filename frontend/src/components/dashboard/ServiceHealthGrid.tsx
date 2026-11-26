import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../../lib/query-keys";
import { getHealth } from "../../api/internal/eval";
import { Card, CardTitle, CardContent, Badge } from "../PlatformUI";
import { cn } from "../../lib/utils";
export function ServiceHealthGrid() {
  const { data } = useQuery({ queryKey: queryKeys.health.all, queryFn: getHealth, refetchInterval: 60_000 });
  const services = (data?.services ?? []) as { name?: string; service?: string; status: string; category?: string; reason?: string }[];
  const label = (s: { name?: string; service?: string }) => s.name ?? s.service ?? "unknown";
  return <Card><CardContent className="pt-5"><CardTitle className="mb-3 flex items-center gap-2 text-sm">Service health <Badge variant="outline">{services.filter(s => s.status === "ok").length}/{services.length}</Badge></CardTitle>
    <div className="flex flex-wrap gap-2">{services.map(s => <span key={label(s)} title={s.reason ?? s.status}
      className={cn("rounded-full border px-2 py-1 text-xs", s.status === "ok" ? "border-green-300 bg-green-50 text-green-700 dark:bg-green-950" : "border-yellow-300 bg-yellow-50 text-yellow-700")}>
      <span className={cn("mr-1 inline-block h-1.5 w-1.5 rounded-full", s.status === "ok" ? "bg-green-500" : "bg-yellow-500")} />{label(s)}</span>)}</div>
  </CardContent></Card>;
}
