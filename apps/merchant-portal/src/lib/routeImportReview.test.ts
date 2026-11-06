import assert from "node:assert/strict";
import test from "node:test";

import { routeImportReviewIndexes } from "./routeImportReview.ts";

test("flags needs_review and address.ambiguous stops", () => {
  const job = {
    stops: [
      { geocode_status: "ok" },
      { geocode_status: "needs_review", candidates: [] },
      { geocode_status: "approximate", issues: ["address.approximate"] },
      { geocode_status: "ok", issues: ["address.ambiguous"] },
    ],
  };
  assert.deepEqual(routeImportReviewIndexes(job), [1, 3]);
});

test("empty / null job has nothing to review", () => {
  assert.deepEqual(routeImportReviewIndexes(null), []);
  assert.deepEqual(routeImportReviewIndexes({ stops: [] }), []);
});
