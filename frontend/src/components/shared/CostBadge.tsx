import { formatCost } from "../../lib/utils";
export function CostBadge({ cost, tokens }: { cost: number; tokens?: number }) {
  return <span title={`${tokens?.toLocaleString() ?? 0} tokens`} className="text-xs text-muted-foreground">{formatCost(cost)}{tokens ? ` · ${tokens.toLocaleString()} tok` : ""}</span>;
}
