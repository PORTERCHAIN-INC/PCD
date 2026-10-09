import { describe, expect, it } from "vitest";
import {
  isHhmm,
  parseHolidays,
  parsePrefixes,
  toggleWeekday,
  waveProblems,
} from "./delivery-promise";

describe("delivery-promise helpers", () => {
  it("validates 24h times and wave windows", () => {
    expect(isHhmm("11:00")).toBe(true);
    expect(isHhmm("24:00")).toBe(false);
    expect(waveProblems([{ code: "pm", cutoff: "11:00", start: "14:00", end: "21:00" }])).toEqual(
      []
    );
    expect(
      waveProblems([{ code: "pm", cutoff: "11:00", start: "21:00", end: "14:00" }])[0]
    ).toMatch(/after start/);
    expect(waveProblems([])).toEqual(["Add at least one wave."]);
  });

  it("parses holidays and prefixes", () => {
    expect(parseHolidays("2026-12-25\n2026-12-25, 2026-01-01\nxmas")).toEqual({
      dates: ["2026-01-01", "2026-12-25"],
      invalid: ["xmas"],
    });
    expect(parsePrefixes("l9, L0 k0a toolong")).toEqual(["L9", "L0", "K0A"]);
  });

  it("toggles weekdays sorted", () => {
    expect(toggleWeekday([0, 1, 2], 6)).toEqual([0, 1, 2, 6]);
    expect(toggleWeekday([0, 1, 2], 1)).toEqual([0, 2]);
  });
});
