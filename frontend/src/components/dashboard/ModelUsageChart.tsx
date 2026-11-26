import { Card, CardTitle, CardContent } from "../PlatformUI";
export function ModelUsageChart({ data }: { data?: Record<string, number> }) {
  return <Card><CardContent className="pt-5"><CardTitle className="mb-3 text-sm">Requests by model</CardTitle>
    {Object.entries(data ?? {}).map(([k, v]) => <div key={k} className="flex justify-between text-xs"><span className="truncate">{k}</span><span>{v}</span></div>)}
    {!data && <div className="text-xs text-muted-foreground">No usage data</div>}
  </CardContent></Card>;
}
