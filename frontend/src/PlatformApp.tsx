import { createHashRouter, RouterProvider } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppShell } from "./components/layout/AppShell";
import ChatPage from "./pages/ChatPage";
import DashboardPage from "./pages/DashboardPage";
import WorkspacesPage from "./pages/WorkspacesPage";
import WorkspaceDetailPage from "./pages/WorkspaceDetailPage";
import ModelsPage from "./pages/ModelsPage";
import AgentsPage from "./pages/AgentsPage";
import WorkflowsPage from "./pages/WorkflowsPage";
import TracesPage from "./pages/TracesPage";
import SettingsPage from "./pages/SettingsPage";
import { ToastHost } from "./components/ToastHost";

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 2, refetchOnWindowFocus: false } } });
const router = createHashRouter([{ path: "/", element: <AppShell />, children: [
  { index: true, element: <ChatPage /> }, { path: "dashboard", element: <DashboardPage /> },
  { path: "workspaces", element: <WorkspacesPage /> }, { path: "workspaces/:id", element: <WorkspaceDetailPage /> },
  { path: "models", element: <ModelsPage /> }, { path: "agents", element: <AgentsPage /> },
  { path: "workflows", element: <WorkflowsPage /> }, { path: "traces", element: <TracesPage /> },
  { path: "settings", element: <SettingsPage /> },
]}]);

export default function PlatformApp() {
  return <QueryClientProvider client={queryClient}><ToastHost /><RouterProvider router={router} /></QueryClientProvider>;
}
