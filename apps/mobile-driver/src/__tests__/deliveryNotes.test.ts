import { describe, expect, it } from "vitest";
import { formatAccessLine } from "../format";

describe("driver access line shows shared delivery options", () => {
  it("adds options + site access once, keeps instructions last", () => {
    expect(
      formatAccessLine({
        access_unit: "1204",
        access_buzzer: "12#",
        call_on_arrival: true,
        delivery_notes: [
          "Leave with concierge / reception",
          "Unit 1204",
          "Buzzer 12#",
          "Call on arrival",
          "Needs help loading / unloading",
          "Site access: Gate 7",
        ],
        special_instructions: "Receiver: Ada",
      })
    ).toBe(
      "Unit 1204 · Buzzer 12# · Call on arrival · Leave with concierge / reception · Needs help loading / unloading · Site access: Gate 7 · Receiver: Ada"
    );
  });
  it("older API without delivery_notes still works", () => {
    expect(formatAccessLine({ access_buzzer: "9" })).toBe("Buzzer 9");
  });
});
