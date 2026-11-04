/** L212: wrong-portal sign-ins get "Access denied" + plain copy, never a raw code. */
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { humanAuthError, isBlockedAccountError, isWrongPortalError } from "./authErrors.ts";

describe("wrong-portal errors", () => {
  for (const code of [
    "admin_user_not_found",
    "driver_user_not_provisioned",
    "identity_conflict:idp_user_is_driver",
    "identity_conflict:idp_user_is_admin",
    "missing_portal_permission",
  ]) {
    it(code, () => {
      assert.equal(isWrongPortalError(code), true);
      const copy = humanAuthError(code);
      assert.ok(!copy.includes("_"), copy);
      assert.ok(!/Could not load your session/.test(copy));
    });
  }
  it("other codes are not access-denied", () => {
    assert.equal(isWrongPortalError("porterchain_api_timeout"), false);
    assert.equal(isWrongPortalError(""), false);
  });
});

describe("L222 blocked accounts", () => {
  it("are recognised", () => {
    assert.equal(isBlockedAccountError("driver_suspended"), true);
    assert.equal(isBlockedAccountError("account_suspended"), true);
    assert.equal(isBlockedAccountError("admin_user_not_found"), false);
  });
});
