import { describe, expect, it } from "vitest";
import { isRetryableReplayStatus, isTransientRejection } from "../replayPolicy";

describe("offline replay policy", () => {
  it("keeps auth/permission/rate/server errors queued", () => {
    for (const s of [401, 403, 408, 429, 500, 502, 503])
      expect(isRetryableReplayStatus(s)).toBe(true);
  });
  it("parks real refusals", () => {
    for (const s of [400, 404, 409, 410, 422]) expect(isRetryableReplayStatus(s)).toBe(false);
  });
  it("revives actions an older build parked on a 403 blip", () => {
    expect(isTransientRejection("Forbidden")).toBe(true);
    expect(isTransientRejection("driver_not_found")).toBe(true);
    expect(isTransientRejection("invalid_transition")).toBe(false);
    expect(isTransientRejection(undefined)).toBe(false);
  });
});

import { MAX_AUTH_RETRIES, shouldPark } from "../replayPolicy";

describe("shouldPark", () => {
  it("retries a 403 a bounded number of times, then parks", () => {
    expect(shouldPark(403, 0)).toBe(false);
    expect(shouldPark(403, MAX_AUTH_RETRIES - 1)).toBe(false);
    expect(shouldPark(403, MAX_AUTH_RETRIES)).toBe(true);
  });
  it("never parks on 5xx or 429; parks 422 immediately", () => {
    expect(shouldPark(503, 99)).toBe(false);
    expect(shouldPark(429, 99)).toBe(false);
    expect(shouldPark(422, 0)).toBe(true);
  });
});
