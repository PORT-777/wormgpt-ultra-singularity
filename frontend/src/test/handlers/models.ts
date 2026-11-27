import { http, HttpResponse } from "msw";
export const modelHandlers = [
  http.get(new RegExp(".*/api/internal/models/catalog$"), () => HttpResponse.json({
    models: [
      { id: "claude-3-haiku", provider: "anthropic", context: 200000, cost_per_1k_in: 0.00025, cost_per_1k_out: 0.00125, strengths: ["fast","cheap"], available: true },
      { id: "gpt-4o-mini", provider: "openai", context: 128000, cost_per_1k_in: 0.00015, cost_per_1k_out: 0.0006, strengths: ["fast","general"], available: false },
      { id: "mistralai/mistral-7b", provider: "openrouter", context: 32000, cost_per_1k_in: 0, cost_per_1k_out: 0, strengths: ["free","general"], available: true },
    ],
  })),
  http.get(new RegExp(".*/api/internal/models/usage$"), () => HttpResponse.json({ by_model: { "claude-3-haiku": { tokens_today: 45230, cost_today: 0.0113 } } })),
  http.get(new RegExp(".*/api/internal/models/cost$"), () => HttpResponse.json({ total_cost_usd: 0.1423, cost_today_usd: 0.0131, cost_by_model: { "claude-3-haiku": 0.0113 } })),
  http.post(new RegExp(".*/api/internal/models/route$"), () => HttpResponse.json({ name: "claude-3-haiku", reason: "best ratio" })),
];
