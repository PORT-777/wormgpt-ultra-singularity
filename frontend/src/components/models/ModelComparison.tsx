import { useModels } from "../../hooks/use-models";
import { Card, CardContent, CardTitle } from "../PlatformUI";
import { formatContext } from "../../lib/utils";
export function ModelComparison() {
  const { data } = useModels();
  const models = data?.models ?? [];
  return <Card><CardContent className="pt-5"><CardTitle className="mb-3 text-sm">Model comparison</CardTitle>
    <div className="overflow-x-auto"><table className="w-full text-xs"><thead><tr className="text-left text-muted-foreground"><th className="p-1">Model</th><th>Context</th><th>In</th><th>Out</th><th>Available</th></tr></thead><tbody>
      {models.map(m => <tr key={m.id} className="border-t"><td className="p-1">{m.id}</td><td>{formatContext(m.context)}</td><td>${m.cost_per_1k_in}</td><td>${m.cost_per_1k_out}</td><td>{m.available ? "yes" : "no key"}</td></tr>)}
    </tbody></table></div>
  </CardContent></Card>;
}
