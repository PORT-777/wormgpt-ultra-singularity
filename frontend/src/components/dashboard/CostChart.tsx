import { Card, CardTitle, CardContent } from "../PlatformUI";
export function CostChart({ data }: { data?: Record<string, number> }) {
  const rows = Object.entries(data ?? {});
  const max = Math.max(1, ...rows.map(r => r[1]));
  return <Card><CardContent className="pt-5"><CardTitle className="mb-3 text-sm">Cost by model</CardTitle>
    {!rows.length && <div className="text-xs text-muted-foreground">No cost data yet</div>}
    {rows.map(([k, v]) => <div key={k} className="mb-2"><div className="flex justify-between text-xs"><span className="truncate">{k}</span><span>${v.toFixed(5)}</span></div><div className="h-1.5 rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${(v/max)*100}%` }} /></div></div>)}
  </CardContent></Card>;
}
