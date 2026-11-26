import { useModelStore } from "../store/model.store";
import { Card, CardContent, CardTitle, Tabs, Badge } from "../components/PlatformUI";
import type { RoutingStrategy } from "../types/model.types";
const STRATEGIES: RoutingStrategy[] = ["cheapest","fastest","best_quality","balanced","task_optimal"];
export default function SettingsPage() {
  const { strategy, setStrategy, selectedModel, setModel } = useModelStore();
  return <div className="max-w-2xl space-y-5 p-6"><h1 className="text-2xl font-bold">Settings</h1>
    <Tabs value="general" onChange={() => {}} items={[{value:"general",label:"General"},{value:"models",label:"Models"},{value:"keys",label:"API Keys"},{value:"appearance",label:"Appearance"}]} />
    <Card><CardContent className="pt-5"><CardTitle className="mb-3 text-sm">Model preferences</CardTitle>
      <label className="text-xs">Default model</label><select value={selectedModel} onChange={e => setModel(e.target.value)} className="mb-3 w-full rounded-md border bg-background p-2 text-xs"><option value="auto/free">auto/free</option>{STRATEGIES.map(() => null)}</select>
      <label className="text-xs">Routing strategy</label><select value={strategy} onChange={e => setStrategy(e.target.value as RoutingStrategy)} className="w-full rounded-md border bg-background p-2 text-xs">{STRATEGIES.map(s => <option key={s}>{s}</option>)}</select>
    </CardContent></Card>
    <Card><CardContent className="pt-5"><CardTitle className="mb-3 text-sm">API keys</CardTitle><div className="text-xs text-muted-foreground"><Badge variant="outline">Keys are server-side only</Badge> — the frontend never receives or displays key values.</div></CardContent></Card>
  </div>;
}
