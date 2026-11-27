import { describe, it, expect } from "vitest";
import { formatCost, formatMs, formatTokens, formatContext, groupBy, truncate } from "../utils";
describe("formatCost", () => {
  it("free for zero", () => expect(formatCost(0)).toBe("free"));
  it("micro dollars", () => expect(formatCost(0.000005)).toMatch(/μ/));
  it("milli dollars", () => expect(formatCost(0.001)).toMatch(/m/));
  it("full dollars", () => expect(formatCost(0.05)).toMatch(/0.05/));
});
describe("formatMs", () => {
  it("ms", () => expect(formatMs(234)).toBe("234ms"));
  it("seconds", () => expect(formatMs(1500)).toBe("1.5s"));
});
describe("formatTokens", () => {
  it("raw", () => expect(formatTokens(500)).toBe("500"));
  it("k", () => expect(formatTokens(45230)).toBe("45.2k"));
  it("M", () => expect(formatTokens(1_240_000)).toBe("1.2M"));
});
describe("formatContext", () => { it("k", () => expect(formatContext(200000)).toBe("200k")); });
describe("groupBy", () => {
  it("groups", () => {
    const r = groupBy([{ type: "a" }, { type: "b" }, { type: "a" }], "type");
    expect(r["a"]).toHaveLength(2); expect(r["b"]).toHaveLength(1);
  });
});
describe("truncate", () => {
  it("unchanged", () => expect(truncate("hello", 10)).toBe("hello"));
  it("truncates", () => expect(truncate("hello world", 5)).toBe("hello…"));
});
