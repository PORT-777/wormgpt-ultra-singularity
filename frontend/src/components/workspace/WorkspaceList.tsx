import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "../../api/client";
import { queryKeys } from "../../lib/query-keys";

type KnowledgeWorkspace = {
  id: string;
  name: string;
  description?: string;
  documents?: string[];
  vector_collection?: string;
  created_at?: string;
};

export function WorkspaceList() {
  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.workspaces.list,
    queryFn: () =>
      apiGet<{ workspaces: KnowledgeWorkspace[] }>("/api/internal/workspaces"),
  });

  if (isLoading)
    return (
      <div className="text-sm text-muted-foreground">Loading workspaces…</div>
    );
  if (error)
    return (
      <div className="text-sm text-destructive">
        Failed to load workspaces — backend unreachable.
      </div>
    );

  const items = data?.workspaces ?? [];
  if (!items.length)
    return (
      <div className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
        No workspaces yet — create one above.
      </div>
    );

  return (
    <div className="divide-y rounded-lg border">
      {items.map((ws) => (
        <Link
          key={ws.id}
          to={`/workspaces/${ws.id}`}
          className="flex items-center justify-between p-4 transition-colors hover:bg-muted/50"
        >
          <div className="min-w-0">
            <div className="truncate font-medium">{ws.name}</div>
            <div className="truncate text-xs text-muted-foreground">
              {ws.description || ws.vector_collection}
            </div>
          </div>
          <div className="shrink-0 text-xs text-muted-foreground">
            {ws.documents?.length ?? 0} docs
          </div>
        </Link>
      ))}
    </div>
  );
}
