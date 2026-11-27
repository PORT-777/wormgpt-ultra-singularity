import { useEffect } from "react";
import { useModels } from "../../hooks/use-models";
import { useModelStore } from "../../store/model.store";
import { formatContext } from "../../lib/utils";
import { Button } from "../PlatformUI";
import { ChevronDown } from "lucide-react";
export function ModelSelector({ compact = false }: { compact?: boolean }) {
  const { data } = useModels();
  const { selectedModel, setModel } = useModelStore();
  const models = data?.models ?? [];
  useEffect(() => {
    if (models.length && selectedModel !== "auto" && !models.some(m => m.id === selectedModel)) setModel("auto");
  }, [models, selectedModel, setModel]);
  if (compact) return <select value={selectedModel} onChange={e => setModel(e.target.value)} className="rounded-md border bg-background px-2 py-1 text-xs">
    <option value="auto">auto (Groq)</option>{models.map(m => <option key={m.id} value={m.id}>{m.id}</option>)}
  </select>;
  return <div className="space-y-2"><div className="flex items-center gap-2 text-sm"><ChevronDown size={14} /> Model: <b>{selectedModel}</b></div>
    <div className="grid gap-2 md:grid-cols-2">{models.map(m => <button key={m.id} onClick={() => setModel(m.id)} className="rounded-lg border p-3 text-left text-xs hover:bg-muted">
      <div className="font-medium">{m.id}</div><div className="text-muted-foreground">{m.provider} · {formatContext(m.context)} ctx · ${m.cost_per_1k_in}/1k</div>
    </button>)}</div></div>;
}
