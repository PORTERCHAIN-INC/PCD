import assert from "node:assert/strict";
import test from "node:test";

import { barcodesFor, custodyStatusLabel, SOURCE_LABEL } from "./partnerBarcodes.ts";

test("custody status labels", () => {
  assert.equal(custodyStatusLabel("missing_at_pickup"), "Missing at pickup");
  assert.equal(custodyStatusLabel("some_new_state"), "some new state");
});

test("barcodes are grouped per box", () => {
  const data = {
    items: [
      { id: "a", package_id: "p1", source: "shopify" as const, value: "X", created_at: null },
      { id: "b", package_id: "p2", source: "merchant" as const, value: "Y", created_at: null },
    ],
    packages: [],
  };
  assert.deepEqual(
    barcodesFor(data, "p1").map((i) => i.id),
    ["a"]
  );
  assert.equal(SOURCE_LABEL.partner_carrier, "Partner carrier");
});
