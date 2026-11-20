// @ts-nocheck
import React, { useState } from "react";

/**
 * Dependency-free Markdown renderer with:
 *  - headings, bold/italic, inline code, links, images
 *  - fenced code + lightweight syntax highlighting
 *  - tables, blockquotes, horizontal rules, task lists
 *  - copy / collapse controls on code blocks
 * Output is built from React elements (never raw HTML) so model output
 * cannot inject markup or scripts.
 */

const KEYWORDS = {
  js: "const let var function return if else for while do switch case break continue new class extends super import from export default async await try catch finally throw typeof instanceof in of this null undefined true false void delete yield static get set",
  py: "def return if elif else for while break continue import from as class try except finally raise with lambda pass global nonlocal assert del yield async await in is not and or None True False self print",
  sh: "if then else elif fi for in do done case esac while function return export local echo cd ls cat grep sed awk sudo apt npm node python pip git docker curl wget chmod mkdir rm cp mv",
  sql: "select from where insert into values update set delete create table alter drop join left right inner outer on group by order having limit offset union all as and or not null primary key foreign references",
  css: "display position color background border margin padding flex grid font width height top left right bottom",
  html: "html head body div span a img script style link meta title header footer main section",
  json: "true false null",
  yaml: "true false null yes no on off",
};
const FAMILY = (lang) => {
  const l = String(lang || "").toLowerCase();
  if (/^(js|jsx|ts|tsx|javascript|typescript|json|jsonc)$/.test(l)) return l === "json" || l === "jsonc" ? "json" : "js";
  if (/^(py|python|py3)$/.test(l)) return "py";
  if (/^(sh|bash|zsh|shell|console|powershell|ps1)$/.test(l)) return "sh";
  if (/^(sql|mysql|postgres|plsql)$/.test(l)) return "sql";
  if (/^(css|scss|less)$/.test(l)) return "css";
  if (/^(html|xml|svg|vue)$/.test(l)) return "html";
  if (/^(yaml|yml|toml|ini|env)$/.test(l)) return "yaml";
  return "";
};

const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

function highlight(code, lang) {
  const fam = FAMILY(lang);
  const kw = KEYWORDS[fam];
  if (!kw) return [code];
  const words = kw.split(/\s+/).filter(Boolean).map(escapeRe).join("|");
  const comment = fam === "py" || fam === "sh" || fam === "yaml" ? "#" : fam === "sql" ? "--" : "//";
  const re = new RegExp(
    `(${escapeRe(comment)}[^\\n]*)|("(?:\\\\.|[^"\\\\])*"|'(?:\\\\.|[^'\\\\])*'|\`(?:\\\\.|[^\`\\\\])*\`)|\\b(${words})\\b|\\b(\\d+(?:\\.\\d+)?)\\b`,
    "g"
  );
  const out = [];
  let last = 0, m, k = 0;
  while ((m = re.exec(code)) !== null) {
    if (m.index > last) out.push(code.slice(last, m.index));
    const cls = m[1] ? "tok-com" : m[2] ? "tok-str" : m[3] ? "tok-kw" : "tok-num";
    out.push(<span key={`t${k++}`} className={cls}>{m[0]}</span>);
    last = m.index + m[0].length;
  }
  if (last < code.length) out.push(code.slice(last));
  return out;
}

function CodeBlock({ lang, code }) {
  const [copied, setCopied] = useState(false);
  const lines = String(code || "").split(/\r?\n/);
  const [collapsed, setCollapsed] = useState(lines.length > 30);
  const copy = async () => {
    try { await navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 1600); } catch { /* ignore */ }
  };
  const shown = collapsed ? lines.slice(0, 26) : lines;
  return (
    <div className={`md-code ${collapsed ? "collapsed" : ""}`}>
      <div className="md-code-head">
        <span className="md-code-lang">{lang || "code"}</span>
        <div className="row" style={{ gap: 6 }}>
          {lines.length > 30 && <button type="button" onClick={() => setCollapsed(v => !v)} className="md-toggle">{collapsed ? "Show all" : "Collapse"}</button>}
          <button type="button" onClick={copy} className="md-copy">{copied ? "Copied" : "Copy"}</button>
        </div>
      </div>
      <pre dir="ltr" className="has-lines">
        <code>{shown.map((ln, i) => <span key={i} className="ln">{highlight(ln, lang)}{i < shown.length - 1 ? "\n" : ""}</span>)}</code>
      </pre>
    </div>
  );
}

const INLINE = /(`[^`\n]+`)|(\*\*[^*\n]+\*\*)|(__[^_\n]+__)|(\*[^*\n]+\*)|(\[[^\]\n]+\]\((?:https?:\/\/|mailto:)[^)\s]+\))|!\[([^\]]*)\]\((https?:\/\/[^)\s]+)\)|\$([^$\n]+)\$/g;

function inline(text) {
  const out = [];
  let last = 0, m, key = 0;
  INLINE.lastIndex = 0;
  while ((m = INLINE.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const token = m[0];
    if (m[1]) {
      out.push(<code key={`c${key++}`} className="md-inline-code">{token.slice(1, -1)}</code>);
    } else if (m[2] || m[3]) {
      out.push(<strong key={`b${key++}`}>{token.slice(2, -2)}</strong>);
    } else if (m[4]) {
      out.push(<em key={`i${key++}`}>{token.slice(1, -1)}</em>);
    } else if (m[5]) {
      const label = token.slice(1, token.indexOf("]"));
      const href = token.slice(token.indexOf("(") + 1, -1);
      out.push(<a key={`a${key++}`} href={href} target="_blank" rel="noreferrer noopener" className="md-link">{label}</a>);
    } else if (m[7] !== undefined) {
      out.push(<img key={`img${key++}`} src={m[7]} alt={m[6] || ""} className="md-img" loading="lazy" />);
    } else if (m[8]) {
      out.push(<span key={`q${key++}`} className="md-math">{m[8]}</span>);
    }
    last = m.index + token.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

const isTableSep = (line) => /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$/.test(line);
const cells = (line) => line.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|").map(s => s.trim());

export default function Markdown({ text }) {
  const source = String(text || "");
  const lines = source.split(/\r?\n/);
  const blocks = [];
  let i = 0, key = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (/^\s*```/.test(line)) {
      const lang = line.replace(/^\s*```/, "").trim();
      const code = [];
      i += 1;
      while (i < lines.length && !/^\s*```/.test(lines[i])) { code.push(lines[i]); i += 1; }
      i += 1;
      blocks.push(<CodeBlock key={`code${key++}`} lang={lang} code={code.join("\n")} />);
      continue;
    }

    if (!line.trim()) { i += 1; continue; }

    if (/^\s*(---|\*\*\*|___)\s*$/.test(line)) { blocks.push(<hr key={`hr${key++}`} className="md-hr" />); i += 1; continue; }

    const heading = line.match(/^\s*(#{1,6})\s+(.*)$/);
    if (heading) {
      const level = heading[1].length;
      const size = level <= 2 ? "text-lg" : level === 3 ? "text-base" : "text-sm";
      blocks.push(<div key={`h${key++}`} className={`md-heading ${size}`}>{inline(heading[2])}</div>);
      i += 1;
      continue;
    }

    // table: header line + separator line
    if (line.includes("|") && i + 1 < lines.length && isTableSep(lines[i + 1])) {
      const head = cells(line);
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].includes("|") && lines[i].trim()) { rows.push(cells(lines[i])); i += 1; }
      blocks.push(
        <div key={`tbl${key++}`} className="md-table-wrap">
          <table className="md-table">
            <thead><tr>{head.map((h, n) => <th key={n}>{inline(h)}</th>)}</tr></thead>
            <tbody>{rows.map((r, ri) => <tr key={ri}>{head.map((_, ci) => <td key={ci}>{inline(r[ci] || "")}</td>)}</tr>)}</tbody>
          </table>
        </div>
      );
      continue;
    }

    if (/^\s*>\s?/.test(line)) {
      const quote = [];
      while (i < lines.length && /^\s*>\s?/.test(lines[i])) { quote.push(lines[i].replace(/^\s*>\s?/, "")); i += 1; }
      blocks.push(<blockquote key={`bq${key++}`} className="md-blockquote">{inline(quote.join(" "))}</blockquote>);
      continue;
    }

    if (/^\s*[-*•]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*[-*•]\s+/.test(lines[i])) { items.push(lines[i].replace(/^\s*[-*•]\s+/, "")); i += 1; }
      blocks.push(
        <ul key={`ul${key++}`} className="md-list">
          {items.map((it, n) => {
            const task = it.match(/^\[([ xX])\]\s*(.*)$/);
            if (task) return <li key={n} className="md-task"><span className={`md-check ${task[1].toLowerCase() === "x" ? "on" : ""}`}>{task[1].toLowerCase() === "x" ? "✓" : ""}</span>{inline(task[2])}</li>;
            return <li key={n}>{inline(it)}</li>;
          })}
        </ul>
      );
      continue;
    }

    if (/^\s*\d+[.)]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*\d+[.)]\s+/.test(lines[i])) { items.push(lines[i].replace(/^\s*\d+[.)]\s+/, "")); i += 1; }
      blocks.push(<ol key={`ol${key++}`} className="md-list md-list-num">{items.map((it, n) => <li key={n}>{inline(it)}</li>)}</ol>);
      continue;
    }

    const para = [line];
    i += 1;
    while (i < lines.length && lines[i].trim() && !/^\s*```/.test(lines[i]) && !/^\s*#{1,6}\s+/.test(lines[i]) && !/^\s*[-*•]\s+/.test(lines[i]) && !/^\s*\d+[.)]\s+/.test(lines[i]) && !/^\s*>\s?/.test(lines[i]) && !/^\s*(---|\*\*\*|___)\s*$/.test(lines[i])) {
      para.push(lines[i]);
      i += 1;
    }
    blocks.push(<p key={`p${key++}`} className="md-para">{inline(para.join(" "))}</p>);
  }

  return <div className="md-body" dir="auto">{blocks}</div>;
}