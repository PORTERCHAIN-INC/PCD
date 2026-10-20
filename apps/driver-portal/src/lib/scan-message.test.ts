import { describe, expect, it } from "vitest";
import { scanResultMessage } from "@/lib/jobs";

describe("scanResultMessage", () => {
  it("confirms a first scan with the count", () => {
    expect(
      scanResultMessage({ tracking_suffix: "PC-1-01", scanned: 1, required: 2, duplicate: false })
    ).toBe("Scanned PC-1-01 (1 of 2)");
  });
  it("flags a repeat scan instead of counting it again", () => {
    expect(
      scanResultMessage({ tracking_suffix: "PC-1-01", scanned: 1, required: 1, duplicate: true })
    ).toBe("Already scanned: PC-1-01 (1 of 1)");
  });
});
