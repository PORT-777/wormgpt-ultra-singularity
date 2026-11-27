import { http, HttpResponse } from "msw";
export const ragHandlers = [
  http.get(new RegExp(".*/api/internal/rag/stats$"), () => HttpResponse.json({ backend: "memory", chunks: 1842, documents: 21 })),
  http.get(new RegExp(".*/api/internal/rag/documents$"), () => HttpResponse.json({ documents: [{ doc_id: "doc-1", chunks: 42 }] })),
  http.post(new RegExp(".*/api/internal/rag/query$"), async ({ request }) => {
    const body = await request.json() as { question: string };
    return HttpResponse.json({ answer: `Answer to ${body.question}`, sources: [{ id: "src-1", title: "Doc", excerpt: "excerpt" }], confidence: 0.87, tokens_used: 820, model_used: "groq" });
  }),
];
