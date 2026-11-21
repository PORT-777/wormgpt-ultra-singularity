// PORT 777 AI — stateless Streamable HTTP MCP server (MCP 2.0 style).
// Every request builds a fresh server instance; no sessions, no stored secrets.
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { createMcpExpressApp } from '@modelcontextprotocol/sdk/server/express.js';
import { z } from 'zod';

const BACKEND = (process.env.PORT777_BACKEND_URL || 'http://127.0.0.1:7777').replace(/\/$/, '');
const TOKEN = process.env.PORT777_API_TOKEN || '';
const MCP_SERVER_URL = process.env.MCP_SERVER_URL || 'https://mcp.port777.ai/mcp';
const UI_DOMAIN = '51e74df0951c76854fa966c64fa536d7.claudemcpcontent.com';

function text(value) {
  return { content: [{ type: 'text', text: JSON.stringify(value, null, 2) }] };
}

async function api(path, options = {}) {
  const headers = { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}) };
  if (TOKEN) headers.Authorization = `Bearer ${TOKEN}`;
  const res = await fetch(`${BACKEND}${path}`, { ...options, headers, signal: AbortSignal.timeout(60000) });
  const body = await res.text();
  let parsed;
  try { parsed = JSON.parse(body); } catch { parsed = body; }
  if (!res.ok) throw new Error(`backend ${res.status}: ${String(body).slice(0, 300)}`);
  return parsed;
}

function buildServer() {
  const server = new McpServer({ name: 'port777-server', version: '1.0.0' });

  server.registerTool('port777_health', {
    title: 'PORT 777 health',
    description: 'Check that the PORT 777 backend and its database are reachable. Use when asked if the platform is online.',
    inputSchema: {},
  }, async () => text(await api('/api/health')));

  server.registerTool('port777_models', {
    title: 'Available AI models',
    description: 'List the real models configured in this PORT 777 deployment. Use before selecting a model for a chat task.',
    inputSchema: {},
  }, async () => text(await api('/api/models')));

  server.registerTool('port777_vendor_repos', {
    title: 'Vendored reference repositories',
    description: 'List the reference repositories and tools available in this deployment. Use when a task could reuse an existing playbook or implementation.',
    inputSchema: {},
  }, async () => text(await api('/api/vendor/tools')));

  server.registerTool('port777_vendor_skill_search', {
    title: 'Search vendor skills',
    description: 'Search SKILL.md playbooks across all vendored repositories. Use when the user asks how to do something that may already have a documented playbook.',
    inputSchema: {
      query: z.string().describe('short English keywords describing the task'),
      limit: z.number().int().min(1).max(40).optional().describe('max results, default 10'),
    },
  }, async ({ query, limit }) => text(await api(`/api/vendor/skills/search?q=${encodeURIComponent(query)}&limit=${limit || 10}`)));

  server.registerTool('port777_computer_providers', {
    title: 'Computer providers',
    description: 'Check whether a real isolated Linux computer provider is configured. Use before creating a sandbox.',
    inputSchema: {},
  }, async () => text(await api('/api/computer/providers')));

  server.registerTool('port777_computer_create', {
    title: 'Create an isolated Linux computer',
    description: 'Create a real temporary or persistent Linux sandbox. Use only when the user explicitly asks for a computer/sandbox.',
    inputSchema: { mode: z.enum(['temporary', 'persistent']).optional().describe('default temporary') },
  }, async ({ mode }) => text(await api('/api/computer/computers', { method: 'POST', body: JSON.stringify({ mode: mode || 'temporary' }) })));

  server.registerTool('port777_computer_execute', {
    title: 'Run a command in a Linux computer',
    description: 'Execute a shell command inside an existing PORT 777 computer and return real stdout, stderr and exit code.',
    inputSchema: {
      computer_id: z.string().describe('id returned by port777_computer_create'),
      command: z.string().describe('shell command to run'),
      timeout: z.number().int().min(1).max(600).optional().describe('seconds, default 60'),
    },
  }, async ({ computer_id, command, timeout }) => text(await api(`/api/computer/computers/${encodeURIComponent(computer_id)}/execute`, {
    method: 'POST', body: JSON.stringify({ command, timeout: timeout || 60 }),
  })));

  server.registerTool('port777_computer_delete', {
    title: 'Delete a Linux computer',
    description: 'Destroy an existing sandbox and release its resources. Use only when the user asks to remove it.',
    inputSchema: { computer_id: z.string() },
  }, async ({ computer_id }) => text(await api(`/api/computer/computers/${encodeURIComponent(computer_id)}`, { method: 'DELETE' })));

  server.registerTool('port777_task_create', {
    title: 'Create a task',
    description: 'Create a persistent task in PORT 777. Use when the user asks to remember, register or track a task.',
    inputSchema: {
      title: z.string().describe('short task title'),
      description: z.string().optional().describe('extra details'),
      priority: z.enum(['low', 'normal', 'high']).optional().describe('default normal'),
      category: z.string().optional().describe('default general'),
    },
  }, async (args) => text(await api('/api/tasks', { method: 'POST', body: JSON.stringify(args) })));

  server.registerTool('port777_task_list', {
    title: 'List tasks',
    description: 'List saved PORT 777 tasks, optionally filtered by status. Use for summaries and daily/weekly reports.',
    inputSchema: { status: z.enum(['open', 'done', 'cancelled']).optional().describe('filter') },
  }, async ({ status }) => text(await api(`/api/tasks${status ? `?status=${status}` : ''}`)));

  server.registerTool('port777_task_complete', {
    title: 'Complete a task',
    description: 'Mark a saved PORT 777 task as done. Use only when the user says the task is finished.',
    inputSchema: { task_id: z.string().describe('id returned by port777_task_create or list') },
  }, async ({ task_id }) => text(await api(`/api/tasks/${encodeURIComponent(task_id)}`, {
    method: 'PATCH', body: JSON.stringify({ status: 'done' }),
  })));

  // MCP App UI: rendered inside the conversation by compatible hosts.
  server.registerTool('port777_dashboard', {
    title: 'PORT 777 dashboard',
    description: 'Show a compact live dashboard of backend health, models and computer providers as an interactive in-chat app.',
    inputSchema: {},
    _meta: { ui: { domain: UI_DOMAIN } },
  }, async () => {
    const [health, models, providers] = await Promise.all([
      api('/api/health'), api('/api/models'), api('/api/computer/providers'),
    ]);
    return {
      content: [{ type: 'text', text: JSON.stringify({ server: MCP_SERVER_URL, health, models, providers }) }],
      _meta: { ui: { domain: UI_DOMAIN } },
    };
  });

  return server;
}

const app = createMcpExpressApp();

app.post('/mcp', async (req, res) => {
  const server = buildServer();
  const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
  res.on('close', () => { transport.close(); server.close(); });
  try {
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch (error) {
    if (!res.headersSent) res.status(500).json({ jsonrpc: '2.0', error: { code: -32000, message: String(error) }, id: null });
  }
});

const notAllowed = (req, res) => res.status(405).json({
  jsonrpc: '2.0', error: { code: -32000, message: 'Method not allowed.' }, id: null,
});
app.get('/mcp', notAllowed);
app.delete('/mcp', notAllowed);

const port = Number(process.env.PORT || 3000);
app.listen(port, '0.0.0.0', (err) => {
  if (err) { console.error(`failed to start: ${err.message}`); process.exit(1); }
  console.log(`port777-server on http://0.0.0.0:${port}/mcp`);
});
