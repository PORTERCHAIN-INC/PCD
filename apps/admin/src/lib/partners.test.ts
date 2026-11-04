import { describe, expect, it } from "vitest";
import { EMPTY_PARTNER, parseCoverage, partnerError } from "./partners";

describe("partners helpers", () => {
  it("validates like the API", () => {
    expect(partnerError(EMPTY_PARTNER)).toMatch(/Name/);
    expect(partnerError({ ...EMPTY_PARTNER, name: "WH", kind: "warehouse" })).toMatch(
      /coordinates/
    );
    expect(partnerError({ ...EMPTY_PARTNER, name: "Fast Courier" })).toBeNull();
  });
  it("parses FSA coverage", () => {
    expect(parseCoverage("m5v, L4 k")).toEqual(["M5V", "L4", "K"]);
  });
});
