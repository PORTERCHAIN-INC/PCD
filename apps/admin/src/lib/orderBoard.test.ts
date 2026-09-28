import { describe, expect, it } from "vitest";
import { boardQuery, periodDates } from "./orderBoard";

const noonToronto = new Date("2026-09-28T16:00:00Z");

describe("order board dates", () => {
  it("uses the Toronto calendar day", () => {
    expect(periodDates("today", "", "", noonToronto)).toEqual({
      date_from: "2026-09-28",
      date_to: "2026-09-28",
    });
    expect(periodDates("yesterday", "", "", noonToronto)).toEqual({
      date_from: "2026-09-27",
      date_to: "2026-09-27",
    });
    expect(periodDates("last7", "", "", noonToronto)).toEqual({
      date_from: "2026-09-22",
      date_to: "2026-09-28",
    });
    expect(periodDates("last_month", "", "", noonToronto)).toEqual({
      date_from: "2026-08-01",
      date_to: "2026-08-31",
    });
  });

  it("keeps older unfinished work only for an open queue", () => {
    const open = boardQuery("today", "needs_decision", "", "", undefined);
    expect(open.include_carryover).toBe(true);
    expect(open.date_field).toBe("scheduled");
    expect(open.queue).toBe("needs_decision");

    const done = boardQuery("today", "done", "", "");
    expect(done.include_carryover).toBeUndefined();
    expect(done.queue).toBe("done");

    const oneStatus = boardQuery("today", "needs_decision", "", "", "FAILED");
    expect(oneStatus.queue).toBeUndefined();
    expect(oneStatus.include_carryover).toBeUndefined();
  });
});
