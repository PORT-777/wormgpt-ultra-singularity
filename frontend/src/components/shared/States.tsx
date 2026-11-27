import React from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

export function EmptyState({ icon, title, description, action }: {
  icon?: React.ReactNode; title: string; description?: string; action?: React.ReactNode;
}) {
  return <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed p-12 text-center">
    {icon && <div className="text-muted-foreground">{icon}</div>}
    <div className="font-semibold">{title}</div>
    {description && <div className="max-w-md text-sm text-muted-foreground">{description}</div>}
    {action}
  </div>;
}

export function LoadingSkeleton({ count = 3 }: { count?: number }) {
  return <div className="space-y-3">{Array.from({ length: count }, (_, i) =>
    <Skeleton key={i} className="h-20 w-full rounded-lg" />)}</div>;
}

export function ErrorState({ message }: { message: string }) {
  return <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">{message}</div>;
}

export class ErrorBoundary extends React.Component<{ children?: React.ReactNode }, { error: string | null }> {
  state = { error: null as string | null };
  static getDerivedStateFromError(e: Error) { return { error: e.message }; }
  render() { return this.state.error ? <ErrorState message={this.state.error} /> : this.props.children; }
}

/** Thin wrapper over shadcn Tabs to preserve the previous items/value API. */
export function TabsBar({ value, onChange, items }: {
  value: string; onChange: (v: string) => void; items: { value: string; label: string }[];
}) {
  return <Tabs value={value} onValueChange={onChange}>
    <TabsList>{items.map(i => <TabsTrigger key={i.value} value={i.value}>{i.label}</TabsTrigger>)}</TabsList>
  </Tabs>;
}
