import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../../lib/query-keys";
import { getTools } from "../../api/internal/agents";
import { Badge, Card, CardContent, CardTitle } from "../PlatformUI";
export function ToolRegistry() {
  const { data } = useQuery({ queryKey: queryKeys.agents.tools, queryFn: getTools });
  const tools = (data?.tools ?? []) as { name: string; description: string; requires: string[] }[];
  return <Card><CardContent className="pt-5"><CardTitle className="mb-3 text-sm">Agent tools ({tools.length})</CardTitle>
    <div className="space-y-2">{tools.map(t => <div key={t.name} className="flex items-center justify-between text-xs"><span className="font-medium">{t.name}</span><span className="truncate text-muted-foreground">{t.description}</span><Badge variant="outline">{t.requires.length ? "keyed" : "free"}</Badge></div>)}</div>
  </CardContent></Card>;
}
