import { useModels } from "../../hooks/use-models";
import { ModelCard } from "./ModelCard";
import { LoadingSkeleton, ErrorState, EmptyState } from "../PlatformUI";
export function ModelCatalog() {
  const { data, isLoading, error } = useModels();
  if (isLoading) return <LoadingSkeleton count={6} />;
  if (error) return <ErrorState message={String(error)} />;
  const models = data?.models ?? [];
  if (!models.length) return <EmptyState title="No models" description="Configure a provider key to see models." />;
  return <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">{models.map(m => <ModelCard key={m.id} model={m} />)}</div>;
}
