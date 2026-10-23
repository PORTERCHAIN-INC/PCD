import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { humanError } from "../errorCopy";

const read = (p: string) => readFileSync(join(__dirname, "..", "..", p), "utf8");

describe("build 29 regressions", () => {
  it("no cash-on-delivery payment link in the driver app (Interac-only)", () => {
    expect(read("src/screens/JobScreen.tsx")).not.toMatch(/cod-due|Open payment link|codCheckout/);
    expect(read("src/api.ts")).not.toMatch(/cod-checkout/);
    expect(read("src/types.ts")).not.toMatch(/codAmountCents|codStatus|cod_amount_cents|cod_status/);
    expect(read("src/handshake.ts")).not.toMatch(/codAmountCents|codStatus|cod_amount_cents/);
  });

  it("an open shift on an older server is resumed, not an error", () => {
    expect(read("src/hooks/useFieldSession.ts")).toMatch(/shift_already_active/);
    expect(humanError("shift_already_active")).toBe(
      "You are already on duty. Pull down to refresh."
    );
  });

  it("action errors are set after the refresh so they stay on screen", () => {
    const app = read("App.tsx");
    const refresh = app.indexOf("await field.refresh();\n      // After the refresh");
    expect(refresh).toBeGreaterThan(0);
    expect(app.indexOf("if (failure) setError(failure);", refresh)).toBeGreaterThan(refresh);
  });
});
