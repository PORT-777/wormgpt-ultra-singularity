import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeAll, afterAll } from "vitest";
import { server } from "./msw-server";

// Same-origin in jsdom: avoids CORS preflight on the mocked internal API.
(import.meta.env as Record<string, unknown>).VITE_API_BASE = "";

let serverActive = true;
export function disableMockServer() {
  if (serverActive) { server.close(); serverActive = false; }
}

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => { cleanup(); if (serverActive) server.resetHandlers(); });
afterAll(() => { if (serverActive) server.close(); });
