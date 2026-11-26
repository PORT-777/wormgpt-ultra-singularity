import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../../lib/query-keys";
import { jobStatus } from "../../api/internal/agents";
import { MarkdownRenderer } from "../shared/MarkdownRenderer";
import { Card, CardContent } from "../PlatformUI";
export function AgentProgress({ jobId }: { jobId: string }) {
  const { data } = useQuery({ queryKey: queryKeys.agents.jobs(jobId), queryFn: () => jobStatus(jobId), refetchInterval: 1500 });
  if (!data) return <div className="text-sm text-muted-foreground">Job {jobId.slice(0, 8)} submitted. Waiting for status…</div>;
  return <Card><CardContent className="pt-5"><div className="mb-3 text-sm font-semibold">Status: {String(data.status ?? "unknown")}</div>
    {data.result ? <MarkdownRenderer content={String(data.result)} /> : <pre className="overflow-x-auto text-xs">{JSON.stringify(data, null, 2)}</pre>}
  </CardContent></Card>;
}
