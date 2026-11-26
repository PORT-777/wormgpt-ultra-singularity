import { Menu } from "lucide-react";
import { Button } from "../PlatformUI";
import { ModelSelector } from "../chat/ModelSelector";
import { useUIStore } from "../../store/ui.store";
export function Header() {
  const toggle = useUIStore(s => s.toggleSidebar);
  return <header className="flex h-12 shrink-0 items-center justify-between border-b px-4">
    <div className="flex items-center gap-2"><Button variant="ghost" size="icon" onClick={toggle} className="md:hidden"><Menu size={16} /></Button><span className="text-sm font-semibold">AI Platform</span></div>
    <ModelSelector compact />
  </header>;
}
