import { Card, CardContent, CardTitle } from "../PlatformUI";
export function NodePanel({ label }: { label: string }) {
  return <Card><CardContent className="pt-4"><CardTitle className="text-xs">{label}</CardTitle><div className="mt-2 text-xs text-muted-foreground">Configure this node in the workflow builder.</div></CardContent></Card>;
}
