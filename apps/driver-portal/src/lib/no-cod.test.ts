import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const read = (p: string) => readFileSync(join(__dirname, "..", "..", p), "utf8");

describe("no cash on delivery (Ravi's no-COD rule)", () => {
  it("driver portal has no COD button, API call or job fields", () => {
    expect(read("src/components/jobs/Delivery360.tsx")).not.toMatch(/Collect COD|cod_checkout|codCheckout|cod_amount_cents/);
    expect(read("src/lib/api.ts")).not.toMatch(/cod-checkout|codCheckout/);
    expect(read("src/lib/jobs.ts")).not.toMatch(/cod_amount_cents|cod_status/);
  });
});
