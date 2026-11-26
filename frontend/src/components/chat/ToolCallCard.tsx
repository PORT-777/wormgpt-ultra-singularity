import { Wrench } from "lucide-react";
export function ToolCallCard({ tool, args, result }: { tool: string; args: unknown; result?: unknown }) {
  return <div className="my-2 rounded-lg border bg-muted/30 p-2 text-xs"><div className="mb-1 flex items-center gap-1 font-medium"><Wrench size={12} />{tool}</div>
    <pre className="overflow-x-auto text-muted-foreground">{JSON.stringify(args)}</pre>
    {result !== undefined && <pre className="mt-1 overflow-x-auto text-green-600">{JSON.stringify(result).slice(0, 400)}</pre>}
  </div>;
}
