import { describe, expect, it } from "vitest";
import { failureSummary, fmtMs, fmtPct, logQuery, outcome } from "./notificationCenter";

describe("notification center helpers", () => {
  it("formats latency numbers-first", () => {
    expect(fmtMs(null)).toBe("—");
    expect(fmtMs(182)).toBe("182 ms");
    expect(fmtMs(2400)).toBe("2.4 s");
    expect(fmtMs(42_000)).toBe("42 s");
    expect(fmtMs(180_000)).toBe("3 min");
  });
  it("formats percentages", () => {
    expect(fmtPct(null)).toBe("—");
    expect(fmtPct(99)).toBe("99%");
    expect(fmtPct(97.25)).toBe("97.3%");
  });
  it("drops empty filters", () => {
    expect(logQuery({ persona: "receiver", q: "  ", status: "" })).toBe(
      "persona=receiver&limit=100"
    );
  });
  it("picks the furthest known outcome", () => {
    expect(outcome({ status: "sent", delivery: "accepted", channel: "email" }).label).toBe(
      "Accepted"
    );
    expect(outcome({ status: "sent", delivery: "opened", channel: "email" })).toEqual({
      label: "Opened",
      tone: "ok",
    });
    expect(outcome({ status: "bounced", delivery: "hard_bounce", channel: "email" }).tone).toBe(
      "bad"
    );
    expect(outcome({ status: "held", delivery: null, channel: "sms" }).label).toBe("Held");
    expect(outcome({ status: "dead_letter", delivery: null, channel: "email" }).label).toBe(
      "Dead letter"
    );
  });
  it("summarises failures per hour", () => {
    expect(failureSummary([{ count: 1 }, { count: 4 }, { count: 2 }])).toEqual({
      last: 2,
      peak: 4,
      total: 7,
    });
    expect(failureSummary([])).toEqual({ last: 0, peak: 0, total: 0 });
  });
});
