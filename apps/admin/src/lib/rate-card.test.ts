import { describe, expect, it } from "vitest";
import { adjustmentError, dollarsToCents, guardrailTone, hoursLeft, pctChange } from "./rate-card";

describe("rate card helpers", () => {
  it("computes % change", () => {
    expect(pctChange(2000, 1800)).toBe(-10);
    expect(pctChange(0, 10)).toBe(0);
  });
  it("colours guardrails", () => {
    expect(guardrailTone(-10)).toBe("ok");
    expect(guardrailTone(-27)).toBe("warn");
    expect(guardrailTone(51)).toBe("blocked");
  });
  it("parses dollars", () => {
    expect(dollarsToCents("$17.50")).toBe(1750);
    expect(dollarsToCents("abc")).toBeNull();
  });
});

describe("quote + adjustment helpers", () => {
  it("hoursLeft counts down and floors at 0", () => {
    const now = Date.parse("2026-10-29T12:00:00Z");
    expect(hoursLeft("2026-11-01T12:00:00Z", now)).toBe(72);
    expect(hoursLeft("2026-10-29T11:00:00Z", now)).toBe(0);
  });
  it("adjustmentError mirrors the API limits", () => {
    expect(adjustmentError(0, "long reason", 1000)).toMatch(/non-zero/);
    expect(adjustmentError(1500, "long reason", 1000)).toMatch(/limit/);
    expect(adjustmentError(-500, "x", 1000)).toMatch(/reason/);
    expect(adjustmentError(-500, "late delivery", 1000)).toBeNull();
  });
});
