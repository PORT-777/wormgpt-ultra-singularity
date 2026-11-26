import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { Button } from "../PlatformUI";
export function CodeBlock({ className, children }: { className?: string; children?: React.ReactNode }) {
  const [copied, setCopied] = useState(false);
  const language = className?.replace("language-", "") ?? "code";
  const copy = () => { navigator.clipboard?.writeText(String(children)); setCopied(true); setTimeout(() => setCopied(false), 1500); };
  return <div className="my-3 overflow-hidden rounded-lg border">
    <div className="flex items-center justify-between bg-muted/50 px-3 py-1.5">
      <span className="font-mono text-xs text-muted-foreground">{language}</span>
      <Button size="icon" variant="ghost" onClick={copy}>{copied ? <Check size={12} /> : <Copy size={12} />}</Button>
    </div>
    <pre className="overflow-x-auto p-3 text-xs"><code>{children}</code></pre>
  </div>;
}
