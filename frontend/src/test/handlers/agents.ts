import { http, HttpResponse } from "msw";
export const agentHandlers = [
  http.get(new RegExp(".*/api/internal/agents/tools$"), () => HttpResponse.json({ tools: [
    { name: "web_search", description: "Search the web", requires: ["SERPAPI_KEY"] },
    { name: "rag_query", description: "Query knowledge base", requires: [] },
  ] })),
  http.post(new RegExp(".*/api/internal/agents/run$"), () => HttpResponse.json({ answer: "Hello", steps: [{ routed_to: "researcher" }] })),
  http.get(new RegExp(".*/api/internal/agents/jobs/job\-1$"), () => HttpResponse.json({ id: "job-1", status: "done", result: "done" })),
];
