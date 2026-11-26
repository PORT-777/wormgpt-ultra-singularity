import { useState } from "react";
import { Card, CardContent, CardTitle } from "../PlatformUI";
export function JobHistory({ onSelect }: { onSelect: (id: string) => void }) {
  const [ids] = useState<string[]>([]);
  return <Card><CardContent className="pt-5"><CardTitle className="mb-3 text-sm">Recent jobs</CardTitle>
    {!ids.length && <div className="text-xs text-muted-foreground">Jobs from this session appear here.</div>}
    {ids.map(id => <button key={id} onClick={() => onSelect(id)} className="block text-xs hover:underline">{id}</button>)}
  </CardContent></Card>;
}
