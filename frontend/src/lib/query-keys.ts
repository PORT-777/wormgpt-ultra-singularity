export const queryKeys = {
  models: { catalog: ["models","catalog"], usage: ["models","usage"], cost: ["models","cost"] },
  metrics: { platform: (p: string) => ["metrics", p], traces: (p: number) => ["traces", p] },
  rag: { documents: ["rag","documents"], stats: ["rag","stats"] },
  workspaces: { list: ["workspaces"], detail: (id: string) => ["workspaces",id], docs: (id: string) => ["workspaces",id,"docs"] },
  sessions: { list: (u: string) => ["sessions",u], detail: (id: string) => ["sessions",id] },
  agents: { tools: ["agents","tools"], jobs: (id: string) => ["agents","jobs",id] },
  health: { all: ["health","all"] },
} as const;
