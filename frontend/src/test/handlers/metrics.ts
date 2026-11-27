import { http, HttpResponse } from "msw";
export const metricHandlers = [
  http.get(new RegExp(".*/api/internal/eval/metrics$"), ({ request }) => HttpResponse.json({
    period: new URL(request.url).searchParams.get("period") ?? "24h",
    total_cost_usd: 2.4521, cost_today_usd: 0.1423,
    cost_by_model: { "claude-3-haiku": 0.08, "gpt-4o-mini": 0.06 },
    total_requests: 8432, requests_today: 342,
    requests_by_model: { "claude-3-haiku": 280, "gpt-4o-mini": 62 },
    cache_hit_rate: 0.34, avg_latency_ms: 824, p50_latency_ms: 710,
    p95_latency_ms: 1820, p99_latency_ms: 3100, error_rate: 0.008,
    total_tokens_used: 1240000, tokens_today: 57300, avg_tokens_per_request: 147,
  })),
  http.get(new RegExp(".*/api/internal/eval/traces$"), () => HttpResponse.json({
    traces: [
      { id: "trace-001", timestamp: Date.now()-60000, model: "claude-3-haiku", trace_type: "llm_call", total_tokens: 460, latency_ms: 823, cost_usd: 0.000287, success: true },
      { id: "trace-002", timestamp: Date.now()-180000, model: "gpt-4o-mini", trace_type: "rag_query", total_tokens: 1070, latency_ms: 1240, cost_usd: 0.000214, success: true },
    ],
  })),
  http.get(new RegExp(".*/api/internal/eval/health/all$"), () => HttpResponse.json({
    status: "degraded", total: 4, ok: 3, services: [
      { name: "openai", category: "AI LLM", status: "ok" },
      { name: "anthropic", category: "AI LLM", status: "ok" },
      { name: "clarifai", category: "AI Vision", status: "degraded" },
      { name: "wolfram", category: "Compute", status: "disabled" },
    ],
  })),
  http.post(new RegExp(".*/api/internal/eval/score$"), () => HttpResponse.json({ faithfulness: 0.9, relevance: 0.8, coherence: 0.9, completeness: 0.7, conciseness: 0.8, overall: 0.82, flags: [] })),
];
