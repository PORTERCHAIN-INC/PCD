import { describe, expect, it } from "vitest";
import { blockOf, fieldError, hm, weeklyHours } from "../account";
import { shouldPersist } from "../data/keys";

describe("account helpers", () => {
  it("maps API field errors to inline copy", () => {
    expect(fieldError(new Error('{"field":"address.postal_code","code":"invalid"}'))).toEqual({
      field: "address.postal_code",
      text: "Check this",
    });
    expect(fieldError(new Error("network_unavailable"))).toBeNull();
  });

  it("formats worked time", () => {
    expect(hm(45)).toBe("45m");
    expect(hm(485)).toBe("8h 05m");
  });

  it("totals weekly availability and recognises presets", () => {
    const empty = { mon: [], tue: [], wed: [], thu: [], fri: [], sat: [], sun: [] };
    expect(
      weeklyHours({
        ...empty,
        mon: [{ start: "08:00", end: "16:00" }],
        sat: [{ start: "09:00", end: "15:30" }],
      })
    ).toBe(14.5);
    expect(blockOf({ start: "07:00", end: "19:00" })).toBe("long");
    expect(blockOf({ start: "05:00", end: "06:00" })).toBe("day");
  });

  it("persists the new screens' data for instant cold start", () => {
    for (const k of ["profile", "pay", "time", "inbox", "tickets"])
      expect(shouldPersist({ queryKey: [k], state: { status: "success" } })).toBe(true);
    expect(shouldPersist({ queryKey: ["profile"], state: { status: "error" } })).toBe(false);
  });
});
