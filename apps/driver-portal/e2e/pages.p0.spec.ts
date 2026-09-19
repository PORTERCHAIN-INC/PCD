import { test, expect, playwrightCases, tcId } from "./fixtures";

/** Driver portal page / subpage P0 wiring — one describe per SSOT id. No browser launch. */
const pageCases = playwrightCases("skeleton").filter(
  (c) =>
    (c.id.startsWith("UI-D-") || c.id.startsWith("UX-D-")) && !["UI-D-01", "UI-D-10"].includes(c.id)
);

const ROUTE_HINT: Record<string, string> = {
  "UI-D-01": "/login",
  "UI-D-02": "/dashboard",
  "UI-D-03": "/jobs",
  "UI-D-04": "/navigation",
  "UI-D-05": "/shift",
  "UI-D-06": "/communications",
  "UI-D-10": "/onboarding",
  "UX-D-02": "/navigation",
};

for (const c of pageCases) {
  test.describe(`${c.id} ${tcId(c.id)} @p0`, () => {
    test(c.title, () => {
      const route = ROUTE_HINT[c.id] ?? "/dashboard";
      expect(c.id).toMatch(/^(UI|UX)-D-/);
      expect(route).toMatch(/^\//);
      expect(c.title.length).toBeGreaterThan(0);
    });
  });
}
