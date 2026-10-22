import assert from "node:assert/strict";
import test from "node:test";

import {
  DROP_METHODS,
  deliveryOptionLines,
  normalizeDeliveryOptions,
} from "../src/deliveryOptions.ts";

test("normalize drops blanks and unknown methods", () => {
  assert.equal(normalizeDeliveryOptions(undefined), undefined);
  assert.equal(normalizeDeliveryOptions({ unit: "  ", drop_method: "nope" }), undefined);
  assert.deepEqual(
    normalizeDeliveryOptions({
      drop_method: "concierge",
      unit: " 1204 ",
      buzzer: "12#",
      call_on_arrival: true,
      load_help: false,
      note: "  Fragile,   glass ",
    }),
    {
      drop_method: "concierge",
      unit: "1204",
      buzzer: "12#",
      call_on_arrival: true,
      note: "Fragile, glass",
    }
  );
});

test("lines match the API summary order", () => {
  assert.deepEqual(
    deliveryOptionLines({
      drop_method: "leave_at_door",
      unit: "4",
      buzzer: "9",
      load_help: true,
      note: "Side door",
    }),
    ["Leave at door", "Unit 4", "Buzzer 9", "Needs help loading / unloading", "Side door"]
  );
  assert.deepEqual(
    DROP_METHODS.map((m) => m.id),
    ["leave_at_door", "hand_to_recipient", "concierge"]
  );
});
