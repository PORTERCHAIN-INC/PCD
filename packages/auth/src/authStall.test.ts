/**
 * Run: node --experimental-strip-types --test packages/auth/src/authStall.test.ts
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { AUTH_STALL_TIMEOUT_MS, isPrimaryButtonBusy, nextStallState } from "./authStall.ts";

describe("auth stall watchdog", () => {
  it("treats loading or disabled buttons as busy", () => {
    assert.equal(isPrimaryButtonBusy(null), false);
    assert.equal(isPrimaryButtonBusy({ disabled: false, loading: false }), false);
    assert.equal(isPrimaryButtonBusy({ disabled: true, loading: false }), true);
    assert.equal(isPrimaryButtonBusy({ disabled: false, loading: true }), true);
  });

  it("flags a stall only after the timeout of continuous busy", () => {
    let s = nextStallState(true, null, 1000);
    assert.deepEqual(s, { busySince: 1000, stalled: false });
    s = nextStallState(true, s.busySince, 1000 + AUTH_STALL_TIMEOUT_MS - 1);
    assert.equal(s.stalled, false);
    s = nextStallState(true, s.busySince, 1000 + AUTH_STALL_TIMEOUT_MS);
    assert.equal(s.stalled, true);
  });

  it("resets when the button becomes idle", () => {
    const s = nextStallState(false, 1000, 99_999);
    assert.deepEqual(s, { busySince: null, stalled: false });
  });
});
