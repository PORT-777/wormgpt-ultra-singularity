import { http, HttpResponse } from "msw";
export const chatHandlers = [
  http.post(new RegExp(".*/api/internal/sessions$"), () => HttpResponse.json({
    id: "sess-abc", user_id: "default", model: "auto", mode: "chat", messages: [], created_at: new Date().toISOString(),
  })),
  http.get(new RegExp(".*/api/internal/sessions/sess\-abc$"), () => HttpResponse.json({
    id: "sess-abc", user_id: "default", model: "auto", mode: "chat", messages: [],
  })),
];
