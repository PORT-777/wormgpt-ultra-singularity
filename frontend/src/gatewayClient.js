// Minimal gateway client used by GatewayPanel/SquadPanel/ModelPicker.
// Endpoints are served by backend gateway.py (mounted under /api/gateway by main.py).

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  const ct = res.headers.get("content-type") || "";
  const data = ct.includes("application/json") ? await res.json().catch(() => ({})) : await res.text();
  if (!res.ok) {
    const msg = (data && (data.detail || data.error || data.message)) || `HTTP ${res.status}`;
    const err = new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

export function maskKey(k) {
  const s = String(k || "");
  if (!s) return "—";
  if (s.length < 9) return s.slice(0, 2) + "••••";
  return s.slice(0, 4) + "••••" + s.slice(-4);
}

export const gatewayApi = {
  getSettings: () => api("/api/gateway/settings"),
  setSettings: (patch) => api("/api/gateway/settings", { method: "POST", body: JSON.stringify(patch || {}) }),
  getTimeline: (sessionId, runId = "", limit = 2000) => api(`/api/timeline/${encodeURIComponent(sessionId)}?run_id=${encodeURIComponent(runId || "")}&limit=${limit}`),
  getSessionRuns: (sessionId, limit = 2000) => api(`/api/history/${encodeURIComponent(sessionId)}/runs?limit=${limit}`),
  getSessionTrace: (sessionId, runId = "", limit = 2000) => api(`/api/history/${encodeURIComponent(sessionId)}/trace?run_id=${encodeURIComponent(runId || "")}&limit=${limit}`),
  getSessionDetail: (sessionId, limit = 500) => api(`/api/history/${encodeURIComponent(sessionId)}/detail?limit=${limit}`),
  exportSession: (sessionId, limit = 2000) => api(`/api/history/${encodeURIComponent(sessionId)}/export?limit=${limit}`),
  compareModels: (body) => api("/api/gateway/compare", { method: "POST", body: JSON.stringify(body || {}) }),
  listProviders: () => api("/api/gateway/providers"),
  addProvider: (p) => {
    const { url, ...provider } = p || {};
    return api("/api/gateway/providers", {
      method: "POST",
      body: JSON.stringify({ ...provider, baseUrl: provider.baseUrl || url }),
    });
  },
  updateProvider: (id, patch) => api(`/api/gateway/providers/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(patch || {}) }),
  deleteProvider: (id) => api(`/api/gateway/providers/${encodeURIComponent(id)}`, { method: "DELETE" }),
  testProvider: (id) => api(`/api/gateway/providers/${encodeURIComponent(id)}/test`, { method: "POST" }),
  listModels: (freeOnly = false, workingOnly = true) => api(`/api/gateway/models?${freeOnly ? "free=1&" : ""}${workingOnly ? "working=1" : "working=0"}`),
  listCatalog: (q = "", provider = "", free = false, limit = 400, offset = 0) => api(`/api/gateway/catalog?q=${encodeURIComponent(q || "")}&provider=${encodeURIComponent(provider || "")}&free=${free ? 1 : 0}&limit=${limit}&offset=${offset}`),
  syncProviderModels: (id) => api(`/api/gateway/providers/${encodeURIComponent(id)}/sync-models`, { method: "POST" }),
  addCustomModel: (body) => api("/api/gateway/custom-models", { method: "POST", body: JSON.stringify(body || {}) }),
  getFreeTierSummary: () => api("/api/free-tier/summary"),
  getCombo: (combo) => api(`/api/combos/${encodeURIComponent(combo || "auto/coding:free")}`),
  planSquad: (body) => api("/api/gateway/squad/plan", { method: "POST", body: JSON.stringify(body || {}) }),

  // Returns an abort() function. Parses SSE lines: `data: {...}` and `data: [DONE]`.
  runSquadStream(body, onEvent, onDone, onError) {
    const ctrl = new AbortController();
    let finished = false;
    const finish = () => { if (!finished) { finished = true; onDone && onDone(); } };
    (async () => {
      try {
        const res = await fetch("/api/gateway/squad/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body || {}),
          signal: ctrl.signal,
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error((data && (data.detail || data.error)) || `HTTP ${res.status}`);
        }
        if (!res.body) throw new Error("No response body");
        const reader = res.body.getReader();
        const dec = new TextDecoder();
        let buf = "";
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += dec.decode(value, { stream: true });
          const parts = buf.split("\n\n");
          buf = parts.pop() || "";
          for (const part of parts) {
            const lines = part.split("\n").filter(Boolean);
            for (const line of lines) {
              if (!line.startsWith("data:")) continue;
              const payload = line.replace(/^data:\s*/, "");
              if (payload === "[DONE]") { finish(); return; }
              try { onEvent && onEvent(JSON.parse(payload)); } catch {}
            }
          }
        }
        finish();
      } catch (e) {
        if (e && e.name === "AbortError") { finish(); return; }
        onError && onError(e);
      }
    })();
    return () => { try { ctrl.abort(); } catch {} };
  },
};
