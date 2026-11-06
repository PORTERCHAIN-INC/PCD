import { describe, expect, it } from "vitest";
import {
  ADMIN_NAV_GROUPS,
  ADMIN_PALETTE_EXTRA,
  ADMIN_TOP_LEVEL_ROUTES,
  adminNavForRole,
} from "@/lib/admin-nav";

const hrefs = (role: string) => adminNavForRole(role).flatMap((g) => g.items.map((i) => i.href));

describe("role-aware admin nav", () => {
  it("super admin sees everything, admin loses only System", () => {
    const all = ADMIN_NAV_GROUPS.flatMap((g) => g.items.map((i) => i.href));
    expect(hrefs("super_admin")).toEqual(all);
    expect(hrefs("admin")).toEqual(all.filter((h) => h !== "/system"));
  });
  it("hides groups a role cannot use", () => {
    expect(hrefs("sales")).not.toContain("/finance/cash");
    expect(hrefs("sales")).toContain("/leads");
    expect(hrefs("sales")).toContain("/leads/attribution");
    expect(hrefs("merchant_success")).toContain("/leads");
    expect(hrefs("finance")).toContain("/leads/attribution");
    expect(hrefs("finance")).not.toContain("/dispatch/plan");
    expect(hrefs("dispatcher")).toContain("/leads");
    expect(hrefs("dispatcher")).not.toContain("/settings");
    expect(hrefs("read_only")).not.toContain("/settings");
  });

  it("keeps accounts in Customers & Orgs and lead pages in CRM", () => {
    const customers = ADMIN_NAV_GROUPS.find((g) => g.id === "customers")!;
    const crm = ADMIN_NAV_GROUPS.find((g) => g.id === "crm")!;
    const insights = ADMIN_NAV_GROUPS.find((g) => g.id === "insights")!;
    expect(customers.items.map((i) => i.href)).toEqual([
      "/merchants",
      "/orgs",
      "/customers",
      "/merchants/duplicates",
    ]);
    expect(crm.items.map((i) => i.href)).toEqual([
      "/leads",
      "/leads/pipeline",
      "/leads/today",
      "/leads/calendar",
      "/leads/agent",
      "/leads/attribution",
    ]);
    expect(insights.items.map((i) => i.href)).not.toContain("/leads/attribution");
  });
  it("has no duplicate hrefs and every top-level route is in nav or palette", () => {
    const nav = ADMIN_NAV_GROUPS.flatMap((g) => g.items.map((i) => i.href));
    expect(new Set(nav).size).toBe(nav.length);
    const reach = new Set([...nav, ...ADMIN_PALETTE_EXTRA.map((e) => e.href)]);
    for (const r of ADMIN_TOP_LEVEL_ROUTES) expect(reach.has(r)).toBe(true);
  });
  it("follows the doc 75 information architecture", () => {
    expect(ADMIN_NAV_GROUPS.map((g) => g.label)).toEqual([
      "Today",
      "Orders",
      "Dispatch",
      "Network",
      "Customers & Orgs",
      "CRM",
      "Billing",
      "Support",
      "Insights",
      "Settings",
    ]);
    const all = ADMIN_NAV_GROUPS.flatMap((g) => g.items.map((i) => i.href));
    expect(all).not.toContain("/dashboard");
    expect(hrefs("dispatcher")).toContain("/account/security");
  });
});
