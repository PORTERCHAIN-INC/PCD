import assert from "node:assert/strict";
import test from "node:test";

import { shopifyBlockingText, shopifyInstallError, shopifyRatesProblem } from "./shopifyStatus.ts";

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
