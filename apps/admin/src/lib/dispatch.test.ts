import { describe, expect, it } from "vitest";
import { isDispatchView, legacyOperationsTarget } from "@/lib/dispatch";
import { ADMIN_NAV_GROUPS, ADMIN_TOP_LEVEL_ROUTES, isNavActive } from "@/lib/admin-nav";

describe("legacy Control Tower links", () => {
  it.each([
    [null, null, "/dispatch/today"],
    ["desk", null, "/dispatch/today"],
    ["board", null, "/dispatch/today"],
    ["orders", null, "/orders"],
    ["attention", null, "/dispatch/exceptions"],
    ["sla", null, "/dispatch/exceptions"],
    ["tools", "optimize", "/dispatch/plan"],
    ["tools", "ai", "/dispatch/plan"],
    ["tools", "utilization", "/dispatch/fleet"],
    ["map", null, "/dispatch/live"],
  ])("%s/%s → %s", (view, tool, target) => {
    expect(legacyOperationsTarget(view, tool)).toBe(target);
  });

  it("validates view slugs", () => {
    expect(isDispatchView("today")).toBe(true);
    expect(isDispatchView("desk")).toBe(false);
  });
});

describe("Dispatch nav", () => {
  const dispatchGroup = ADMIN_NAV_GROUPS.find((g) => g.id === "operations")!;

  it("is Today, Plan, Live, Exceptions, Orders, Fleet, Metrics", () => {
    expect(dispatchGroup.label).toBe("Dispatch");
    expect(dispatchGroup.items.map((i) => i.label)).toEqual([
      "Today",
      "Plan",
      "Live",
      "Exceptions",
      "Orders",
      "Fleet",
      "Metrics",
    ]);
  });

  it("moves Booking Drafts to the growth/sales group and Drivers into Fleet", () => {
    const growth = ADMIN_NAV_GROUPS.find((g) => g.id === "growth")!;
    expect(growth.items.some((i) => i.href === "/booking-drafts")).toBe(true);
    expect(dispatchGroup.items.some((i) => i.href === "/booking-drafts")).toBe(false);
    expect(ADMIN_NAV_GROUPS.flatMap((g) => g.items).some((i) => i.href === "/drivers")).toBe(false);
    expect(isNavActive("/drivers/abc", "/dispatch/fleet")).toBe(true);
  });

  it("lists every nav href as a top-level route", () => {
    for (const item of ADMIN_NAV_GROUPS.flatMap((g) => g.items)) {
      expect(ADMIN_TOP_LEVEL_ROUTES as readonly string[]).toContain(item.href.split("?")[0]);
    }
  });
});

describe("phase 2 plan helpers", () => {
  it("summarises the pickup/drop mix of a route", async () => {
    const { routeMix } = await import("./dispatch");
    const s = (kind: string) => ({ key: kind + Math.random(), order_id: "o", kind, fsa: "M5H", eta_s: 0 }) as never;
    expect(routeMix([s("pickup"), s("drop"), s("drop"), s("drop")])).toBe("1 pickup · 3 drops");
    expect(routeMix([s("return_pickup"), s("pickup"), s("return_drop")])).toBe("2 pickups · 1 drop");
  });
  it("formats minutes", async () => {
    const { minutes } = await import("./dispatch");
    expect(minutes(59 * 60)).toBe("59m");
    expect(minutes(125 * 60)).toBe("2h 5m");
  });
  it("labels every stop kind", async () => {
    const { STOP_KIND_LABEL } = await import("./dispatch");
    expect(Object.keys(STOP_KIND_LABEL).sort()).toEqual(
      ["drop", "handoff", "hub", "pickup", "return_drop", "return_pickup"]
    );
  });
});

describe("groupStops", () => {
  it("merges consecutive split stops of one order at one place", async () => {
    const { groupStops } = await import("./dispatch");
    const st = (key: string, kind: string, eta_s: number) => ({ key, order_id: key.split(":")[0], kind, fsa: "M5H", eta_s }) as never;
    const g = groupStops([st("a:p0:0", "pickup", 60), st("a:p0:1", "pickup", 120), st("a:d0:0", "drop", 600), st("b:p0:0", "pickup", 900)]);
    expect(g.map((x) => [x.kind, x.count, x.eta_s])).toEqual([["pickup", 2, 120], ["drop", 1, 600], ["pickup", 1, 900]]);
  });
});
