import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { EmptyState, LoadingSkeleton, ErrorState, TabsBar } from "../States";
import { CodeBlock } from "../CodeBlock";
import { CostBadge } from "../CostBadge";

describe("shared states", () => {
  it("renders empty state", () => {
    render(<EmptyState title="Nothing here" description="Create one" />);
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
    expect(screen.getByText("Create one")).toBeInTheDocument();
  });

  it("renders skeletons", () => {
    const { container } = render(<LoadingSkeleton count={3} />);
    expect(container.querySelectorAll("[data-slot='skeleton']").length).toBe(3);
  });

  it("renders error", () => {
    render(<ErrorState message="broken" />);
    expect(screen.getByText("broken")).toBeInTheDocument();
  });

  it("renders tabs", () => {
    render(<TabsBar value="a" onChange={vi.fn()} items={[{ value: "a", label: "A" }, { value: "b", label: "B" }]} />);
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
  });
});

describe("CodeBlock", () => {
  it("copies code", () => {
    const write = vi.fn();
    Object.defineProperty(navigator, "clipboard", { value: { writeText: write }, configurable: true });
    render(<CodeBlock className="language-python">{"print(1)"}</CodeBlock>);
    expect(screen.getByText("python")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button"));
    expect(write).toHaveBeenCalled();
  });
});

describe("CostBadge", () => {
  it("formats cost and tokens", () => {
    render(<CostBadge cost={0.00001} tokens={42} />);
    expect(document.body.textContent).toContain("42");
  });
});
