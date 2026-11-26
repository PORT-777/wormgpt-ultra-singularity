import { NavLink } from "react-router-dom";
import { Activity, Bot, Database, LayoutDashboard, MessageSquare, Settings, Workflow, Cpu } from "lucide-react";
import { cn } from "../../lib/utils";
const ITEMS = [
  { to: "/", label: "Chat", icon: MessageSquare },
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/workspaces", label: "Workspaces", icon: Database },
  { to: "/models", label: "Models", icon: Cpu },
  { to: "/agents", label: "Agents", icon: Bot },
  { to: "/workflows", label: "Workflows", icon: Workflow },
  { to: "/traces", label: "Traces", icon: Activity },
  { to: "/settings", label: "Settings", icon: Settings },
];
export function Sidebar() {
  return <aside className="hidden w-56 shrink-0 border-r bg-muted/20 p-3 md:block">
    <div className="mb-4 px-2 text-sm font-bold">AI Platform</div>
    <nav className="space-y-1">{ITEMS.map(i => <NavLink key={i.to} to={i.to} end={i.to === "/"}
      className={({ isActive }) => cn("flex items-center gap-2 rounded-md px-3 py-2 text-sm", isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted")}>
      <i.icon size={15} />{i.label}
    </NavLink>)}</nav>
  </aside>;
}
