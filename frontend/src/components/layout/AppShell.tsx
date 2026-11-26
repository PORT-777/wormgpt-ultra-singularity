import { Outlet } from "react-router-dom";
import { ErrorBoundary } from "../PlatformUI";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { MobileNav } from "./MobileNav";
export function AppShell() {
  return <div className="flex h-screen flex-col overflow-hidden">
    <Header />
    <div className="flex min-h-0 flex-1">
      <Sidebar />
      <main className="min-w-0 flex-1 overflow-y-auto"><ErrorBoundary><Outlet /></ErrorBoundary></main>
    </div>
    <MobileNav />
  </div>;
}
