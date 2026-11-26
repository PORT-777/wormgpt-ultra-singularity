import { useState } from "react";
import { MetricsGrid } from "../components/dashboard/MetricsGrid";
import { CostChart } from "../components/dashboard/CostChart";
import { LatencyChart } from "../components/dashboard/LatencyChart";
import { ModelUsageChart } from "../components/dashboard/ModelUsageChart";
import { CacheHitChart } from "../components/dashboard/CacheHitChart";
import { ServiceHealthGrid } from "../components/dashboard/ServiceHealthGrid";
import { RecentTraces } from "../components/dashboard/RecentTraces";
import { useMetrics } from "../hooks/use-metrics";
import { Tabs, ErrorState, LoadingSkeleton } from "../components/PlatformUI";
export default function DashboardPage() {
  const [period, setPeriod] = useState("24h");
  const { data, isLoading, error } = useMetrics(period);
  if (isLoading) return <div className="p-6"><LoadingSkeleton count={6} /></div>;
  if (error) return <div className="p-6"><ErrorState message={"Metrics unavailable: " + String(error)} /></div>;
  const m = data ?? {};
  return <div className="space-y-5 p-6"><div className="flex flex-wrap items-center justify-between gap-3">
    <h1 className="text-2xl font-bold">Dashboard</h1>
    <Tabs value={period} onChange={setPeriod} items={["1h","24h","7d","30d"].map(p => ({ value: p, label: p }))} />
  </div>
    <MetricsGrid metrics={m} />
    <div className="grid gap-4 md:grid-cols-3"><CostChart data={m.cost_by_model as Record<string, number>} /><LatencyChart metrics={m} /><CacheHitChart rate={Number(m.cache_hit_rate ?? 0)} /></div>
    <ModelUsageChart data={m.requests_by_model as Record<string, number>} />
    <ServiceHealthGrid /><RecentTraces />
  </div>;
}
