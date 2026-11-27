import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MessageBubble } from "../MessageBubble";
const user = { id: "m1", role: "user" as const, content: "Hello", timestamp: Date.now() };
const assistant = { id: "m2", role: "assistant" as const, content: "2+2 equals **4**.", model: "claude-3-haiku", tokens: 42, cost: 0.00001, timestamp: Date.now() };
describe("MessageBubble", () => {
  it("user message", () => { render(<MessageBubble message={user} />); expect(screen.getByText("Hello")).toBeInTheDocument(); });
  it("assistant markdown", () => { render(<MessageBubble message={assistant} />); expect(document.querySelector("strong")).toBeTruthy(); });
  it("model badge", () => { render(<MessageBubble message={assistant} />); expect(screen.getByText("claude-3-haiku")).toBeInTheDocument(); });
  it("sources", () => { render(<MessageBubble message={{...assistant, sources: [{id:"s1",title:"Math Guide",url:"https://e.com"}]}} />); expect(screen.getByText("Sources")).toBeInTheDocument(); });
});
