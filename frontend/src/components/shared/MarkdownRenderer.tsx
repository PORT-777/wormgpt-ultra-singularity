import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github-dark.css";
import { CodeBlock } from "./CodeBlock";

export function MarkdownRenderer({ content }: { content: string }) {
  return <div className="prose prose-sm dark:prose-invert max-w-none">
    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}
      components={{
        code({ className, children, ...props }: { className?: string; children?: React.ReactNode }) {
          if (className) return <CodeBlock className={className}>{String(children)}</CodeBlock>;
          return <code {...props} className="rounded bg-muted px-1 py-0.5 text-sm">{children}</code>;
        },
        a({ href, children }: { href?: string; children?: React.ReactNode }) {
          return <a href={href} target="_blank" rel="noreferrer" className="text-primary underline">{children}</a>;
        },
      }}>{content}</ReactMarkdown>
  </div>;
}
