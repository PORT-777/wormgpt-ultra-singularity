import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ModelCard } from "../ModelCard";
import { useModelStore } from "@/store/model.store";
vi.mock("@/store/model.store", () => ({ useModelStore: vi.fn() }));
const model = { id: "claude-3-haiku", provider: "anthropic", context: 200000, cost_per_1k_in: 0.00025, cost_per_1k_out: 0.00125, strengths: ["fast","cheap"], available: true };
function mockStore(selected: string, setModel = vi.fn()) {
  vi.mocked(useModelStore).mockReturnValue({ selectedModel: selected, setModel } as any);
  return setModel;
}
describe("ModelCard", () => {
  it("renders info", () => { mockStore(""); render(<ModelCard model={model} />); expect(screen.getByText("claude-3-haiku")).toBeInTheDocument(); expect(screen.getByText(/200k/)).toBeInTheDocument(); });
  it("shows FREE", () => { mockStore(""); render(<ModelCard model={{...model, cost_per_1k_in: 0}} />); expect(screen.getByText("FREE")).toBeInTheDocument(); });
  it("calls setModel", () => { const set = mockStore(""); render(<ModelCard model={model} />); fireEvent.click(screen.getByText("Use model")); expect(set).toHaveBeenCalledWith("claude-3-haiku"); });
  it("selected state", () => { mockStore("claude-3-haiku"); render(<ModelCard model={model} />); expect(screen.getByText("Selected")).toBeInTheDocument(); });
});
