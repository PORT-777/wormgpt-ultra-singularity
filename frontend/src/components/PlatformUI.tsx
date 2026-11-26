import React from "react";
import { cn } from "../lib/utils";

export function Card({ className, children }: { className?: string; children?: React.ReactNode }) {
  return <div className={cn("rounded-xl border bg-card text-card-foreground shadow-sm", className)}>{children}</div>;
}
export function CardHeader({ className, children }: { className?: string; children?: React.ReactNode }) {
  return <div className={cn("flex flex-col space-y-1.5 p-5", className)}>{children}</div>;
}
export function CardTitle({ className, children }: { className?: string; children?: React.ReactNode }) {
  return <h3 className={cn("font-semibold leading-none tracking-tight", className)}>{children}</h3>;
}
export function CardContent({ className, children }: { className?: string; children?: React.ReactNode }) {
  return <div className={cn("p-5 pt-0", className)}>{children}</div>;
}
export function Button({ className, variant = "default", size = "default", ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default"|"outline"|"ghost"|"destructive"; size?: "default"|"sm"|"icon" }) {
  const v = variant === "outline" ? "border bg-transparent hover:bg-muted" :
            variant === "ghost" ? "bg-transparent hover:bg-muted" :
            variant === "destructive" ? "bg-red-600 text-white hover:bg-red-700" :
            "bg-primary text-primary-foreground hover:opacity-90";
  const s = size === "sm" ? "h-8 px-3 text-xs" : size === "icon" ? "h-8 w-8" : "h-9 px-4 text-sm";
  return <button {...props} className={cn("inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors disabled:opacity-50", v, s, className)} />;
}
export function Badge({ className, children, variant = "default" }: { className?: string; children?: React.ReactNode; variant?: "default"|"outline"|"secondary" }) {
  const v = variant === "outline" ? "border bg-transparent" : variant === "secondary" ? "bg-muted" : "bg-primary/10 text-primary";
  return <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium", v, className)}>{children}</span>;
}
export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cn("flex h-9 w-full rounded-md border bg-transparent px-3 text-sm outline-none focus:ring-2 focus:ring-primary/40", className)} />;
}
export function Textarea({ className, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={cn("flex min-h-[80px] w-full rounded-md border bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/40", className)} />;
}
export function Progress({ value }: { value: number }) {
  return <div className="h-2 w-full rounded-full bg-muted"><div className="h-full rounded-full bg-primary transition-all" style={{ width: `${Math.max(0, Math.min(100, value))}%` }} /></div>;
}
export function Tabs({ value, onChange, items }: { value: string; onChange: (v: string) => void; items: { value: string; label: string }[] }) {
  return <div className="flex gap-1 rounded-lg border bg-muted/40 p-1">{items.map(i => (
    <button key={i.value} onClick={() => onChange(i.value)} className={cn("rounded-md px-3 py-1.5 text-xs font-medium", value === i.value ? "bg-background shadow" : "text-muted-foreground")}>{i.label}</button>
  ))}</div>;
}
export function EmptyState({ icon, title, description, action }: { icon?: React.ReactNode; title: string; description?: string; action?: React.ReactNode }) {
  return <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed p-12 text-center">
    {icon && <div className="text-muted-foreground">{icon}</div>}
    <div className="font-semibold">{title}</div>
    {description && <div className="max-w-md text-sm text-muted-foreground">{description}</div>}
    {action}
  </div>;
}
export function LoadingSkeleton({ count = 3 }: { count?: number }) {
  return <div className="space-y-3">{Array.from({ length: count }, (_, i) => <div key={i} className="h-20 animate-pulse rounded-lg bg-muted" />)}</div>;
}
export function ErrorState({ message }: { message: string }) {
  return <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">{message}</div>;
}
export class ErrorBoundary extends React.Component<{ children?: React.ReactNode }, { error: string | null }> {
  state = { error: null as string | null };
  static getDerivedStateFromError(e: Error) { return { error: e.message }; }
  render() { return this.state.error ? <ErrorState message={this.state.error} /> : this.props.children; }
}
