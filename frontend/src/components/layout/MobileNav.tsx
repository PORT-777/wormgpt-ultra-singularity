import { NavLink } from "react-router-dom";
import { Activity, Bot, Database, MessageSquare } from "lucide-react";
export function MobileNav() {
  const items = [{ to: "/", icon: MessageSquare }, { to: "/workspaces", icon: Database }, { to: "/agents", icon: Bot }, { to: "/traces", icon: Activity }];
  return <nav className="flex shrink-0 border-t md:hidden">{items.map(i => <NavLink key={i.to} to={i.to} className="flex flex-1 justify-center py-3 text-muted-foreground"><i.icon size={18} /></NavLink>)}</nav>;
}
