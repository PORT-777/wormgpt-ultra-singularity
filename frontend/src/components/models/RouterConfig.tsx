import { useModelStore } from "../../store/model.store";
import type { RoutingStrategy } from "../../types/model.types";
import { Card, CardContent, CardTitle, Badge } from "../PlatformUI";
const STRATEGIES: RoutingStrategy[] = ["cheapest","fastest","best_quality","balanced","task_optimal"];
export function RouterConfig() {
  const { strategy, setStrategy } = useModelStore();
  return <Card><CardContent className="pt-5"><CardTitle className="mb-3 text-sm">Routing strategy</CardTitle>
    <div className="flex flex-wrap gap-2">{STRATEGIES.map(s => <button key={s} onClick={() => setStrategy(s)}><Badge variant={strategy === s ? "default" : "outline"} className="cursor-pointer">{s}</Badge></button>)}</div>
  </CardContent></Card>;
}
