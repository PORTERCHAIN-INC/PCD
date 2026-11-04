import assert from "node:assert/strict";
import test from "node:test";

import { splitHstLine } from "../../../../packages/ui/src/quote-hst.ts";
import { batchStatusLabel } from "../../../../packages/types/src/batchStatus.ts";

test("HST line is pulled out of pre-tax lines so QuoteLines shows it once", () => {
  const { pretax, hstCents } = splitHstLine([
    { code: "base", amount_cents: 6500 },
    { code: "downtown", amount_cents: 2500 },
    { code: "hst", amount_cents: 1170 },
  ]);
  assert.deepEqual(
    pretax.map((l) => l.code),
    ["base", "downtown"]
  );
  assert.equal(hstCents, 1170);
});

test("legacy breakdowns without an hst line keep every line", () => {
  const { pretax, hstCents } = splitHstLine([{ code: "base", amount_cents: 100 }]);
  assert.equal(pretax.length, 1);
  assert.equal(hstCents, null);
});

test("batch completed renders as a Completed badge", () => {
  assert.equal(batchStatusLabel("completed").label, "Completed");
});
