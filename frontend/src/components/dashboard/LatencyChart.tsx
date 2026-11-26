import { Card, CardTitle, CardContent } from "../PlatformUI";
import { formatMs } from "../../lib/utils";
export function LatencyChart({ metrics }: { metrics: Record<string, unknown> }) {
  const rows = [["avg", metrics.avg_latency_ms], ["p50", metrics.p50_latency_ms], ["p95", metrics.p95_latency_ms], ["p99", metrics.p99_latency_ms]] as [string, unknown][];
  return <Card><CardContent className="pt-5"><CardTitle className="mb-3 text-sm">Latency</CardTitle>{rows.map(([k, v]) => <div key={k} className="flex justify-between text-xs"><span>{k}</span><span>{formatMs(Number(v ?? 0))}</span></div>)}</CardContent></Card>;
}
