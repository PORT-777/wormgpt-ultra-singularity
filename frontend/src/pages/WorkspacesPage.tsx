import { CreateWorkspace } from "../components/workspace/CreateWorkspace";
import { WorkspaceList } from "../components/workspace/WorkspaceList";
export default function WorkspacesPage() { return <div className="space-y-5 p-6">
  <div><h1 className="text-2xl font-bold">Knowledge Workspaces</h1><p className="text-sm text-muted-foreground">Isolated knowledge bases with RAG chat</p></div>
  <div className="max-w-md"><CreateWorkspace /></div><WorkspaceList />
</div>; }
