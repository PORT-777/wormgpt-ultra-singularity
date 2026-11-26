import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../lib/query-keys";
import { getTraces } from "../api/internal/eval";
import type { Trace } from "../types/api.types";
import { Card, Button, ErrorState, LoadingSkeleton } from "../components/PlatformUI";
import { formatCost, formatMs } from "../lib/utils";
export default function TracesPage() {
  const [page, setPage] = useState(0);
  const { data, isLoading, error } = useQuery({ queryKey: queryKeys.metrics.traces(page), queryFn: () => getTraces(50) });
  if (isLoading) return <div className="p-6"><LoadingSkeleton count={4} /></div>;
  if (error) return <div className="p-6"><ErrorState message={String(error)} /></div>;
  const rows = (data?.traces ?? []) as Trace[];
  return <div className="space-y-4 p-6"><h1 className="text-2xl font-bold">LLM Traces</h1><Card><div className="overflow-x-auto"><table className="w-full text-xs"><thead><tr className="border-b text-left text-muted-foreground"><th className="p-3">Time</th><th>Model</th><th>Tokens</th><th>Cost</th><th>Latency</th><th>Status</th></tr></thead><tbody>
    {rows.map(t => <tr key={t.id} className="border-b"><td className="p-3">{t.timestamp ? new Date(t.timestamp).toLocaleString() : "—"}</td><td>{t.model ?? "—"}</td><td>{t.total_tokens ?? 0}</td><td>{formatCost(Number(t.cost_usd ?? 0))}</td><td>{formatMs(Number(t.latency_ms ?? 0))}</td><td className={t.success === false ? "text-red-500" : "text-green-600"}>{t.success === false ? "failed" : "ok"}</td></tr>)}
  </tbody></table></div>{!rows.length && <div className="p-6 text-center text-sm text-muted-foreground">No traces yet.</div>}</Card>
  <div className="flex justify-center gap-2"><Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(p => Math.max(0, p - 1))}>Previous</Button><span className="py-1 text-xs">Page {page + 1}</span><Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)}>Next</Button></div>
</div>;
}
