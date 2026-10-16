import { describe, expect, it, vi } from "vitest";

vi.mock("react-native", () => ({ Platform: { OS: "ios" } }));

describe("release config never points at localhost", async () => {
  const { resolveApiBaseUrl } = await import("./config");
  it("falls back to production in release builds", () => {
    expect(resolveApiBaseUrl("http://localhost:8001", false)).toBe("https://api.porterchain.com");
    expect(resolveApiBaseUrl(undefined, false)).toBe("https://api.porterchain.com");
  });
  it("allows local API only in dev", () => {
    expect(resolveApiBaseUrl(undefined, true, "android")).toBe("http://10.0.2.2:8001");
  });
});
