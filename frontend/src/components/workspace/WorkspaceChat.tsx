import { useState } from "react";
import { apiPost } from "../../api/client";

type ChatReply = {
  answer?: string;
  sources?: { source?: string; score?: number }[];
  workspace?: string;
  error?: string;
};

export function WorkspaceChat({ workspaceId }: { workspaceId: string }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<
    { role: "user" | "assistant"; text: string }[]
  >([]);
  const [busy, setBusy] = useState(false);

  async function send() {
    const q = question.trim();
    if (!q || !workspaceId || busy) return;
    setMessages((m) => [...m, { role: "user", text: q }]);
    setQuestion("");
    setBusy(true);
    try {
      const reply = await apiPost<ChatReply>(
        `/api/internal/workspaces/${workspaceId}/chat`,
        { question: q }
      );
      if (reply.error)
        setMessages((m) => [
          ...m,
          { role: "assistant", text: `Error: ${reply.error}` },
        ]);
      else
        setMessages((m) => [
          ...m,
          { role: "assistant", text: reply.answer || "(empty answer)" },
        ]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: "Request failed — backend unreachable." },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-3 overflow-y-auto p-6">
        {messages.length === 0 && (
          <div className="text-sm text-muted-foreground">
            Ask anything about this workspace's knowledge base.
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={
              m.role === "user"
                ? "text-sm"
                : "rounded-lg border bg-muted/30 p-3 text-sm"
            }
          >
            <span className="mr-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {m.role}
            </span>
            <span className="whitespace-pre-wrap">{m.text}</span>
          </div>
        ))}
      </div>
      <form
        className="flex gap-2 border-t p-4"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask the workspace…"
          className="w-full rounded-md border bg-transparent px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-ring"
        />
        <button
          type="submit"
          disabled={busy || !question.trim()}
          className="shrink-0 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
        >
          {busy ? "Thinking…" : "Send"}
        </button>
      </form>
    </div>
  );
}
