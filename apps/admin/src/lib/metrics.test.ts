import { describe, expect, it } from "vitest";
import { fmtMetric } from "./metrics";

describe("fmtMetric", () => {
  it("formats ratios, money and strings", () => {
    expect(fmtMetric("roic", 0.202)).toBe("20.2%");
    expect(fmtMetric("revenue", 85536)).toBe("$85,536");
    expect(fmtMetric("per_stop", 8.06)).toBe("8.06");
    expect(fmtMetric("colour", "yellow")).toBe("yellow");
  });
});
