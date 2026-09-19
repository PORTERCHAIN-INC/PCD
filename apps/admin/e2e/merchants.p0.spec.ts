import { test, expect } from "./fixtures";

/**
 * Admin merchant-module P0 skeletons (AD-* from docs/testing/merchant_p0_registry.json).
 * Contract wiring — no Chromium launch until status=implemented.
 */
const CASES: { id: string; title: string; route: string }[] = [
  { id: "AD-LIST-001", title: "Admin /merchants list", route: "/merchants" },
  { id: "AD-360-001", title: "Merchant 360 overview tab", route: "/merchants" },
  { id: "AD-360-006", title: "Merchant 360 pricing tab", route: "/merchants" },
  { id: "AD-360-007", title: "Merchant 360 people/team tab", route: "/merchants" },
];

for (const c of CASES) {
  test.describe(`${c.id} @${c.id} @p0`, () => {
    test(c.title, () => {
      expect(c.id).toMatch(/^AD-/);
      expect(c.route).toMatch(/^\//);
      expect(c.title.length).toBeGreaterThan(0);
    });
  });
}
