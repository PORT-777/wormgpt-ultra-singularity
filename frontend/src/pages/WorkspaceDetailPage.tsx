import { useParams } from "react-router-dom";
import { useState } from "react";
import { DocumentUpload } from "../components/workspace/DocumentUpload";
import { DocumentList } from "../components/workspace/DocumentList";
import { WorkspaceChat } from "../components/workspace/WorkspaceChat";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../lib/query-keys";
import { apiGet } from "../api/client";
export default function WorkspaceDetailPage() {
  const { id = "" } = useParams();
  const [docs] = useState<string[]>([]);
  const { data } = useQuery({ queryKey: queryKeys.workspaces.detail(id), queryFn: () => apiGet<{ name?: string }>(`/api/internal/workspaces`) , enabled: false });
  return <div className="flex h-full"><div className="w-80 shrink-0 border-r"><div className="border-b p-4 text-sm font-semibold">{data?.name ?? "Workspace"}</div>
    <DocumentUpload workspaceId={id} /><DocumentList docs={docs} /></div><div className="min-w-0 flex-1"><WorkspaceChat workspaceId={id} /></div></div>;
}
