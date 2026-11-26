import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }
export function formatCost(cost: number): string {
  if (!cost) return "$0";
  return cost < 0.001 ? `$${(cost * 1000).toFixed(3)}m` : `$${cost.toFixed(4)}`;
}
export function formatMs(ms: number): string { return ms >= 1000 ? `${(ms/1000).toFixed(2)}s` : `${Math.round(ms)}ms`; }
export function formatContext(n: number): string { return n >= 1000 ? `${Math.round(n/1000)}k` : String(n); }
