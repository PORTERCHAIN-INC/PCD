import { describe, expect, it } from "vitest";
import { cascadeSummary, confirmMatches, daysLeft } from "./deleted-items";

describe("deleted items helpers", () => {
  it("summarises cascades", () => {
    expect(cascadeSummary({ order: 3, parcel: 1 })).toBe("3 orders, 1 parcel");
    expect(cascadeSummary({ booking_template: 2 })).toBe("2 booking templates");
    expect(cascadeSummary({})).toBe("");
  });

  it("counts days to auto-delete", () => {
    const now = Date.parse("2026-10-13T12:00:00Z");
    expect(daysLeft("2026-10-20T12:00:00Z", now)).toBe(7);
    expect(daysLeft("2026-10-01T00:00:00Z", now)).toBe(0);
    expect(daysLeft(null, now)).toBeNull();
  });

  it("needs the exact label to purge", () => {
    expect(confirmMatches("Kaylulu", "Kaylulu")).toBe(true);
    expect(confirmMatches(" Kaylulu ", "Kaylulu")).toBe(true);
    expect(confirmMatches("kaylulu", "Kaylulu")).toBe(false);
    expect(confirmMatches("", "")).toBe(false);
  });
});
