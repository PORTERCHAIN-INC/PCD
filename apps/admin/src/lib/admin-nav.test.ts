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
    expect(hrefs("finance")).not.toContain("/dispatch/plan");
    expect(hrefs("dispatcher")).not.toContain("/settings");
    expect(hrefs("read_only")).not.toContain("/settings");
  });
  it("has no duplicate hrefs and every top-level route is in nav or palette", () => {
    const nav = ADMIN_NAV_GROUPS.flatMap((g) => g.items.map((i) => i.href));
    expect(new Set(nav).size).toBe(nav.length);
    const reach = new Set([...nav, ...ADMIN_PALETTE_EXTRA.map((e) => e.href)]);
    for (const r of ADMIN_TOP_LEVEL_ROUTES) expect(reach.has(r)).toBe(true);
  });
});
