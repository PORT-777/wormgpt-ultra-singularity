import { Card, CardTitle, CardContent } from "../PlatformUI";
export function CacheHitChart({ rate }: { rate: number }) {
  return <Card><CardContent className="pt-5"><CardTitle className="mb-3 text-sm">Semantic cache</CardTitle><div className="text-2xl font-bold">{(rate * 100).toFixed(1)}%</div><div className="text-xs text-muted-foreground">hit rate</div></CardContent></Card>;
}
