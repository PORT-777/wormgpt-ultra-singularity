import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../../lib/query-keys";
import { getTraces } from "../../api/internal/eval";
import { Card, CardTitle, CardContent } from "../PlatformUI";
import type { Trace } from "../../types/api.types";
import { formatCost, formatMs } from "../../lib/utils";
export function RecentTraces() {
  const { data } = useQuery({ queryKey: queryKeys.metrics.traces(0), queryFn: () => getTraces(20) });
  const rows = (data?.traces ?? []) as Trace[];
  return <Card><CardContent className="pt-5"><CardTitle className="mb-3 text-sm">Recent LLM traces</CardTitle>
    <div className="space-y-1">{rows.slice().reverse().slice(0, 10).map(t => <div key={t.id} className="flex justify-between border-b py-1 text-xs">
      <span className="truncate">{t.model ?? "unknown"}</span><span>{formatMs(Number(t.latency_ms ?? 0))}</span><span>{formatCost(Number(t.cost_usd ?? 0))}</span>
      <span className={t.success === false ? "text-red-500" : "text-green-500"}>{t.success === false ? "fail" : "ok"}</span></div>)}
      {!rows.length && <div className="text-xs text-muted-foreground">No traces recorded yet</div>}
    </div></CardContent></Card>;
}
