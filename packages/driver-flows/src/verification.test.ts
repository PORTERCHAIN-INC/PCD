import { describe, expect, it } from "vitest";
import { riskLevel, verificationBlockers } from "./verification";

const low = [{ barcode: "A" }, { barcode: "B" }, { barcode: "C" }];
describe("verification by risk", () => {
  it("levels", () => {
    expect(riskLevel(low)).toBe("low");
    expect(riskLevel([{ barcode: "X", handling: ["customs"] }])).toBe("high");
    expect(riskLevel([...low, { barcode: "X", handling: ["pharmacy"] }])).toBe("mixed");
  });
  it("blocks until count, photo, confirm and required scans", () => {
    const ps = [...low, { barcode: "X", handling: ["high_value"] }];
    const b = verificationBlockers(ps, ["A"], {
      counted: null,
      photo: false,
      merchantConfirmed: false,
      scanned: [],
    });
    expect(b).toEqual([
      "count_required",
      "photo_required",
      "merchant_confirm_required",
      "scan_required:A",
      "scan_required:X",
    ]);
    expect(
      verificationBlockers(ps, ["A"], {
        counted: 4,
        photo: true,
        merchantConfirmed: true,
        scanned: ["A", "X"],
      })
    ).toEqual([]);
  });
});
