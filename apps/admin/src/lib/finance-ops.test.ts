import { describe, expect, it } from "vitest";
import { quarterRange } from "./finance-ops";

describe("quarterRange", () => {
  it("returns calendar quarters for GST/HST filing", () => {
    const now = new Date(2026, 9, 9); // Oct 9 2026
    expect(quarterRange(0, now)).toEqual({ start: "2026-10-01", end: "2026-12-31", label: "Q4 2026" });
    expect(quarterRange(-1, now)).toEqual({ start: "2026-07-01", end: "2026-09-30", label: "Q3 2026" });
    expect(quarterRange(-4, now).label).toBe("Q4 2025");
  });
});
