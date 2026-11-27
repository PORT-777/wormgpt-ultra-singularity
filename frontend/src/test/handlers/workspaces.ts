import { http, HttpResponse } from "msw";
export const workspaceHandlers = [
  http.get(new RegExp(".*/api/internal/workspaces$"), () => HttpResponse.json({ workspaces: [
    { id: "ws-001", name: "Product Docs", description: "Internal docs", documents: ["README.pdf"], llm_model: "auto", created_at: new Date().toISOString() },
    { id: "ws-002", name: "Legal Contracts", description: "Contracts", documents: [], llm_model: "auto", created_at: new Date().toISOString() },
  ] })),
  http.post(new RegExp(".*/api/internal/workspaces$"), () => HttpResponse.json({ id: "ws-new", name: "New Workspace", documents: [], created_at: new Date().toISOString() }, { status: 201 })),
  http.post(new RegExp(".*/api/internal/workspaces/ws\-001/chat$"), () => HttpResponse.json({ answer: "workspace answer", sources: [] })),
];
