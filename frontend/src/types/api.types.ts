export interface ApiResult<T> { data: T; available?: boolean; reason?: string; }
export interface HealthItem { name: string; category?: string; status: string; reason?: string; }
export interface HealthDashboard { status: string; total: number; ok: number; services: HealthItem[]; }
export interface Trace { id: string; timestamp?: string; model?: string; total_tokens?: number; cost_usd?: number; latency_ms?: number; success?: boolean; trace_type?: string; }
