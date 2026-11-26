import { Activity, DollarSign, Database, Zap } from "lucide-react";
import { Card, CardContent, CardTitle } from "../PlatformUI";
import { formatMs } from "../../lib/utils";
export function MetricsGrid({ metrics }: { metrics: Record<string, unknown> }) {
  const cards = [
    { title: "Cost today", value: `$${Number(metrics.cost_today_usd ?? 0).toFixed(4)}`, icon: DollarSign },
    { title: "Requests", value: String(metrics.requests_today ?? 0), icon: Zap },
    { title: "Cache hit", value: `${(Number(metrics.cache_hit_rate ?? 0) * 100).toFixed(1)}%`, icon: Database },
    { title: "Avg latency", value: formatMs(Number(metrics.avg_latency_ms ?? 0)), icon: Activity },
  ];
  return <div className="grid grid-cols-2 gap-3 md:grid-cols-4">{cards.map(c => <Card key={c.title}><CardContent className="pt-5"><div className="text-xs text-muted-foreground">{c.title}</div><div className="flex items-center gap-2 text-xl font-bold"><c.icon size={16} />{c.value}</div></CardContent></Card>)}</div>;
}
