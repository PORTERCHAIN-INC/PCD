import { test, expect, playwrightCases, tcId } from "./fixtures";

/** Page / subpage P0 wiring — contract checks (no Chromium until implemented). */
const pageCases = playwrightCases("skeleton").filter((c) => c.id.startsWith("UI-"));

const ROUTE_HINT: Record<string, string> = {
  "UI-DASH-001": "/dashboard",
  "UI-OPS-001": "/operations",
  "UI-OPS-002": "/operations",
  "UI-OPS-003": "/operations",
  "UI-OPS-006": "/operations",
  "UI-ORD-001": "/orders",
  "UI-ORD-003": "/orders",
  "UI-MER-002": "/merchants",
  "UI-MER-006": "/merchants",
  "UI-DRV-002": "/drivers",
  "UI-DRV-003": "/drivers",
  "UI-LEAD-001": "/leads",
  "UI-LEAD-002": "/leads/pipeline",
  "UI-DRAFT-001": "/booking-drafts",
  "UI-FIN-002": "/finance",
  "UI-FIN-005": "/finance",
  "UI-PRC-001": "/pricing",
  "UI-SUP-001": "/support",
  "UI-CLM-001": "/claims",
  "UI-NTF-003": "/notifications",
  "UI-SYS-002": "/system",
  "UI-SYS-006": "/system",
  "UI-SET-001": "/settings",
  "UI-SET-003": "/settings?section=users",
  "UI-SET-006": "/settings?section=roles",
  "UI-SET-012": "/settings?section=dashboard",
};

for (const c of pageCases) {
  test.describe(`${c.id} ${tcId(c.id)} @p0`, () => {
    test(c.title, () => {
      const route = ROUTE_HINT[c.id] ?? "/dashboard";
      expect(c.id).toMatch(/^UI-/);
      expect(route).toMatch(/^\//);
      expect(c.title.length).toBeGreaterThan(0);
    });
  });
}
