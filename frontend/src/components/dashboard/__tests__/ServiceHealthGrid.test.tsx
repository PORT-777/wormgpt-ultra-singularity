import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ServiceHealthGrid } from "../ServiceHealthGrid";
function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}
describe("ServiceHealthGrid", () => {
  it("renders services from mock", async () => {
    render(<ServiceHealthGrid />, { wrapper });
    await waitFor(() => expect(screen.getByText("openai")).toBeInTheDocument());
    expect(screen.getByText("anthropic")).toBeInTheDocument();
    expect(screen.getByText("clarifai")).toBeInTheDocument();
  });
  it("renders a health summary", async () => {
    render(<ServiceHealthGrid />, { wrapper });
    await waitFor(() => expect(screen.getByText(/Service health/i)).toBeInTheDocument());
  });
});
