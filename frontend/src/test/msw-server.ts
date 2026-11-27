import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { modelHandlers } from "./handlers/models";
import { metricHandlers } from "./handlers/metrics";
import { chatHandlers } from "./handlers/chat";
import { workspaceHandlers } from "./handlers/workspaces";
import { agentHandlers } from "./handlers/agents";
import { ragHandlers } from "./handlers/rag";
const preflight = http.options(/.*\/api\/.*/, () => new HttpResponse(null, {
  status: 204,
  headers: {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "content-type,x-internal-key",
    "Access-Control-Allow-Methods": "GET,POST,PATCH,DELETE,OPTIONS",
  },
}));

export const server = setupServer(preflight, ...modelHandlers, ...metricHandlers, ...chatHandlers, ...workspaceHandlers, ...agentHandlers, ...ragHandlers);
