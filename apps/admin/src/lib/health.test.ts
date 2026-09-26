import { describe, expect, it } from "vitest";
import { healthStatus, normalizeCheckStatus } from "./health";

describe("normalizeCheckStatus", () => {
  it("maps readiness tokens to the Jeff Dean triad", () => {
    expect(normalizeCheckStatus("ok")).toBe("healthy");
    expect(normalizeCheckStatus("configured")).toBe("healthy");
    expect(normalizeCheckStatus("degraded")).toBe("warning");
    expect(normalizeCheckStatus("unconfigured")).toBe("warning");
    expect(normalizeCheckStatus("error: boom")).toBe("critical");
  });
});

describe("healthStatus", () => {
  it("reads string and {status} shapes", () => {
    expect(healthStatus("ok")).toBe("healthy");
    expect(healthStatus({ status: "degraded" })).toBe("warning");
    expect(healthStatus({ status: "healthy", raw: "ok" })).toBe("healthy");
    expect(healthStatus(null)).toBe("unknown");
  });
});
