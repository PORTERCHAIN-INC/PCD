import { describe, expect, it } from "vitest";
import { relativeTime } from "./crmFormat";

describe("relativeTime (L183)", () => {
  it("shows future times as ahead, not 'just now'", () => {
    expect(relativeTime(new Date(Date.now() + 4 * 3600_000).toISOString())).toBe("in 4h");
    expect(relativeTime(new Date(Date.now() + 20 * 60_000).toISOString())).toBe("in 20m");
  });
  it("keeps past wording", () => {
    expect(relativeTime(new Date(Date.now() - 5 * 60_000).toISOString())).toBe("5m ago");
    expect(relativeTime(new Date().toISOString())).toBe("just now");
  });
});
