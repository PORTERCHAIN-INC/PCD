import { describe, expect, it } from "vitest";
import { formatAccessLine } from "./jobs";

describe("driver portal shows shared delivery options", () => {
  it("merges API lines without repeating unit/buzzer", () => {
    expect(
      formatAccessLine({
        access_unit: "4",
        delivery_notes: ["Hand to recipient only", "Unit 4", "Site access: Gate 7"],
        special_instructions: "Fragile",
      })
    ).toBe("Unit 4 · Hand to recipient only · Site access: Gate 7 · Fragile");
  });
});
