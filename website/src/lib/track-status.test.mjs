import { test } from "node:test";
import assert from "node:assert/strict";
import { trackStatus } from "./track-status.ts";

test("order states collapse to five public steps", () => {
  assert.deepEqual(trackStatus("BOOKED"), { kind: "progress", step: 0 });
  assert.deepEqual(trackStatus("DRIVER_EN_ROUTE"), { kind: "progress", step: 1 });
  assert.deepEqual(trackStatus("PICKED_UP"), { kind: "progress", step: 2 });
  assert.deepEqual(trackStatus("IN_TRANSIT"), { kind: "progress", step: 3 });
  assert.deepEqual(trackStatus("POD_COMPLETED"), { kind: "progress", step: 4 });
  assert.deepEqual(trackStatus("IN_TRANSIT", true), { kind: "progress", step: 4 });
  assert.deepEqual(trackStatus("CANCELLED"), { kind: "exception", state: "CANCELLED" });
});
