import { BookOpen } from "lucide-react";
import type { ModelInfo } from "../../types/model.types";
import { useModelStore } from "../../store/model.store";
import { Card, CardContent, CardTitle, Badge, Button } from "../PlatformUI";
import { formatContext, cn } from "../../lib/utils";
export function ModelCard({ model }: { model: ModelInfo }) {
  const { selectedModel, setModel } = useModelStore();
  const selected = selectedModel === model.id;
  return <Card className={cn("transition-shadow hover:shadow-md", selected && "ring-2 ring-primary")}><CardContent className="pt-5">
    <div className="flex items-start justify-between"><div><CardTitle className="text-sm">{model.id}</CardTitle><Badge variant="outline" className="mt-1">{model.provider}</Badge></div>
      {model.cost_per_1k_in === 0 ? <Badge className="bg-green-500">FREE</Badge> : <span className="text-xs text-muted-foreground">${model.cost_per_1k_in}/1k</span>}</div>
    <div className="mt-3 flex items-center gap-1 text-xs text-muted-foreground"><BookOpen size={12} />{formatContext(model.context)} context</div>
    <div className="mt-2 flex flex-wrap gap-1">{model.strengths.map(s => <Badge key={s} variant="secondary">{s}</Badge>)}</div>
    <Button size="sm" className="mt-3 w-full" variant={selected ? "default" : "outline"} onClick={() => setModel(model.id)}>{selected ? "Selected" : "Use model"}</Button>
  </CardContent></Card>;
}
