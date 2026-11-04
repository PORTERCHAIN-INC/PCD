import assert from "node:assert/strict";
import test from "node:test";

import { BATCH_TONE_CLASS, batchStatusLabel } from "../src/batchStatus.ts";

test("completed batches read Completed with success tone", () => {
  assert.deepEqual(batchStatusLabel("completed"), { label: "Completed", tone: "success" });
  assert.match(BATCH_TONE_CLASS.success, /green/);
});

test("known and unknown statuses get readable labels", () => {
  assert.equal(batchStatusLabel("planned").label, "Planned");
  assert.equal(batchStatusLabel("pickup_failed").tone, "danger");
  assert.equal(batchStatusLabel("return_to_depot").label, "Return to depot");
  assert.equal(batchStatusLabel(undefined).label, "Unknown");
});
