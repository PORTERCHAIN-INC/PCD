import assert from "node:assert/strict";
import test from "node:test";

import {
  shopifyAdvisoryTexts,
  shopifyBlockingText,
  shopifyInstallError,
  shopifyRatesProblem,
} from "./shopifyStatus.ts";

test("advisories are plain reminders and skip unknown codes", () => {
  assert.deepEqual(shopifyAdvisoryTexts(undefined), []);
  const [copy] = shopifyAdvisoryTexts(["carrier_rates_enable_in_shipping", "unknown"]);
  assert.match(copy ?? "", /Shipping and delivery/);
  assert.equal(shopifyAdvisoryTexts(["returns_scope_reapprove"]).length, 1);
});

test("rates copy only says live when the carrier is registered", () => {
  assert.equal(shopifyRatesProblem("ready"), null);
  assert.match(shopifyRatesProblem("carrier_plan_unsupported") ?? "", /plan/);
  assert.match(shopifyRatesProblem(null) ?? "", /did not accept/);
  assert.match(shopifyRatesProblem("something_new") ?? "", /did not accept/);
});

test("install errors are human sentences, never codes", () => {
  assert.equal(shopifyInstallError(""), null);
  assert.match(shopifyInstallError("shop_already_connected") ?? "", /another PorterChain account/);
  assert.doesNotMatch(shopifyInstallError("weird_code") ?? "", /weird_code/);
});

test("blocking codes become one sentence", () => {
  assert.equal(shopifyBlockingText([]), null);
  assert.equal(
    shopifyBlockingText(["carrier_not_registered", "unknown"]),
    "Not live yet: checkout rates are not registered in Shopify."
  );
});

test("a refused Shopify token asks for re-approval, not the shipping scope", () => {
  const copy = shopifyRatesProblem("token_reauth_required") ?? "";
  assert.match(copy, /approve access again/);
  assert.doesNotMatch(copy, /shipping permission/);
  assert.equal(
    shopifyBlockingText(["token_reauth_required"]),
    "Not live yet: reopen the app from Shopify admin to approve access again."
  );
});
