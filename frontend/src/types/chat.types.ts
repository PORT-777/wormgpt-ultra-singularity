export type MessageRole = "user" | "assistant" | "system" | "tool";
export type ChatMode = "chat" | "rag" | "agent";
export interface Source { id: string; title: string; url?: string; excerpt?: string; page?: number; }
export interface AgentStep { agent: string; content: string; timestamp: number; }
export interface ToolCall { tool: string; args: unknown; result?: unknown; }
export interface ChatMessage {
  id: string; role: MessageRole; content: string; model?: string; tokens?: number; cost?: number;
  sources?: Source[]; agentSteps?: AgentStep[]; toolCalls?: ToolCall[]; streaming?: boolean; timestamp: number;
}
