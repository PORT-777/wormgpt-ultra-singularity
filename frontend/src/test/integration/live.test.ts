import { describe, it, expect, beforeAll } from "vitest";
import axios from "axios";
import { disableMockServer } from "../setup";
const LIVE = import.meta.env.VITE_TEST_LIVE === "true";
const BASE = "http://127.0.0.1:7777";
const KEY = import.meta.env.VITE_INTERNAL_API_KEY ?? "test-key";
const client = axios.create({ baseURL: BASE, headers: { "x-internal-key": KEY }, timeout: 15000 });
const dIf = (c: boolean) => c ? describe : describe.skip;
dIf(LIVE)("LIVE integration", () => {
  beforeAll(() => disableMockServer());
  it("models catalog", async () => {
    const { data, status } = await client.get("/api/internal/models/catalog");
    expect(status).toBe(200); expect(Object.keys(data.models ?? {}).length).toBeGreaterThan(0);
  });
  it("metrics", async () => {
    const { data, status } = await client.get("/api/internal/eval/metrics?period=24h");
    expect(status).toBe(200); expect(typeof data.requests_today).toBe("number");
  });
  it("health", async () => {
    const { data, status } = await client.get("/api/internal/eval/health/all");
    expect(status).toBe(200); expect(data.services.length).toBeGreaterThanOrEqual(10);
  }, 30000);
  it("tools", async () => {
    const { data, status } = await client.get("/api/internal/agents/tools");
    expect(status).toBe(200); expect(data.tools.length).toBeGreaterThan(0);
  });
  it("rejects missing key", async () => {
    await expect(axios.get(`${BASE}/api/internal/models/catalog`, { timeout: 5000 })).rejects.toMatchObject({ response: { status: 401 } });
  });
});
