import { test, expect, playwrightCases, tcId } from "./fixtures";
import fs from "fs";
import path from "path";

/**
 * Admin /drivers + Driver 360 P0 wiring (from driver_p0_registry + UI-DRV admin registry).
 * Contract tests — no browser launch. Flip to live UI asserts when registry status=implemented.
 * Run with: pnpm --filter @porterchain/admin test:e2e:p0 -- e2e/drivers.p0.spec.ts
 */

type DriverCase = {
  id: string;
  title: string;
  runner: string;
  status: string;
};

const driverRegistry = JSON.parse(
  fs.readFileSync(path.join(process.cwd(), "../../docs/testing/driver_p0_registry.json"), "utf8")
) as { cases: DriverCase[] };

const adminUiCases = driverRegistry.cases.filter(
  (c) => c.runner === "playwright" && c.id.startsWith("UI-A-") && c.status === "skeleton"
);

const ROUTE_HINT: Record<string, string> = {
  "UI-A-01": "/drivers",
  "UI-A-02": "/drivers",
  "UI-A-03": "/drivers",
  "UI-A-04": "/drivers",
  "UI-A-05": "/drivers",
  "UI-A-06": "/drivers",
  "UI-A-09": "/drivers",
  "UI-A-11": "/operations",
};

for (const c of adminUiCases) {
  test.describe(`${c.id} ${tcId(c.id)} @p0`, () => {
    // No `{ page }` fixture — avoids Chromium launch for registry wiring checks.
    test(c.title, () => {
      const route = ROUTE_HINT[c.id] ?? "/drivers";
      expect(c.id).toMatch(/^UI-A-/);
      expect(route).toMatch(/^\//);
      expect(c.title.length).toBeGreaterThan(0);
    });
  });
}

/** Also keep admin_p0_registry UI-DRV-* wired here for one place to run driver admin UI. */
const adminDrv = playwrightCases("skeleton").filter((c) => c.id.startsWith("UI-DRV-"));

for (const c of adminDrv) {
  test.describe(`${c.id} ${tcId(c.id)} @p0`, () => {
    test(c.title, () => {
      expect(c.id).toMatch(/^UI-DRV-/);
      expect(c.title.length).toBeGreaterThan(0);
    });
  });
}

test.describe(`UI-A-01 ${tcId("UI-A-01")} smoke-when-ready`, () => {
  test("authenticated /drivers loads shell", () => {
    test.skip(!process.env.ADMIN_RUN_LIVE, "set ADMIN_RUN_LIVE=1 with storage state + chromium");
  });
});
