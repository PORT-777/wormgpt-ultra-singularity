import { Button } from "../PlatformUI";
export function WorkflowList({ onSelect }: { onSelect: (id: string) => void }) {
  return <div className="space-y-2"><Button className="w-full" size="sm" onClick={() => onSelect("new")}>+ New workflow</Button>
    <div className="text-xs text-muted-foreground">Workflows are stored in the backend; this builder submits them through the job queue.</div></div>;
}
