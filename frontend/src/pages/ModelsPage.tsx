import { RouterConfig } from "../components/models/RouterConfig";
import { CostProjection } from "../components/models/CostProjection";
import { ModelCatalog } from "../components/models/ModelCatalog";
import { ModelComparison } from "../components/models/ModelComparison";
export default function ModelsPage() { return <div className="space-y-6 p-6">
  <h1 className="text-2xl font-bold">Model Management</h1>
  <div className="grid gap-4 md:grid-cols-2"><RouterConfig /><CostProjection /></div>
  <ModelComparison /><ModelCatalog />
</div>; }
