import type { Source } from "../../types/chat.types";
export function SourceCards({ sources }: { sources: Source[] }) {
  return <div className="mt-3"><p className="mb-2 text-xs font-medium text-muted-foreground">Sources</p>
    <div className="flex gap-2 overflow-x-auto pb-2">{sources.map((s, i) => <a key={s.id} href={s.url || "#"} target="_blank" rel="noreferrer" className="w-48 shrink-0 rounded-lg border p-2 text-xs hover:bg-muted">
      <div className="mb-1 flex items-center gap-2"><span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-xs text-primary-foreground">{i + 1}</span><span className="truncate text-muted-foreground">{s.url ? new URL(s.url).hostname : "Internal"}</span></div>
      <div className="line-clamp-2 font-medium">{s.title}</div>{s.excerpt && <div className="mt-1 line-clamp-2 text-muted-foreground">{s.excerpt}</div>}
    </a>)}</div></div>;
}
