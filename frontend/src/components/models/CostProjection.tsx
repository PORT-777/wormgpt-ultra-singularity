import { useQuery } from "@tanstack/react-query";
import { getProjection } from "../../api/internal/eval";
import { Card, CardContent, CardTitle } from "../PlatformUI";
export function CostProjection() {
  const { data } = useQuery({ queryKey: ["cost","projection"], queryFn: getProjection, refetchInterval: 60_000 });
  return <Card><CardContent className="pt-5"><CardTitle className="mb-2 text-sm">Cost projection</CardTitle>
    <div className="text-2xl font-bold">${Number(data?.projected_monthly_usd ?? 0).toFixed(4)}</div><div className="text-xs text-muted-foreground">projected monthly from last 24h</div>
  </CardContent></Card>;
}
