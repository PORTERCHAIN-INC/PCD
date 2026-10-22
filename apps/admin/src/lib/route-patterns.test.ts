import { describe, expect, it } from "vitest";
import { routePatterns, type PlanStop } from "./dispatch";

const st = (order_id: string, kind: PlanStop["kind"]): PlanStop => ({
  key: `${order_id}:${kind}`,
  order_id,
  kind,
  fsa: "M5V",
  eta_s: 0,
});
const ids = (stops: PlanStop[]) => routePatterns(stops).map((p) => p.id);

describe("routePatterns", () => {
  it("pickup-only to warehouse", () => {
    expect(ids([st("a", "pickup"), st("a", "hub")])).toEqual(["pickup_to_warehouse"]);
  });
  it("warehouse to delivery", () => {
    expect(ids([st("a", "hub"), st("a", "drop")])).toEqual(["warehouse_to_delivery"]);
  });
  it("same driver pickup and delivery", () => {
    expect(ids([st("a", "pickup"), st("a", "drop")])).toEqual(["same_driver"]);
  });
  it("mixed and multi on one route", () => {
    const got = ids([st("a", "pickup"), st("a", "drop"), st("b", "pickup"), st("b", "drop")]);
    expect(got).toEqual(["same_driver", "mixed", "multi"]);
  });
  it("every pattern carries a tooltip", () => {
    for (const p of routePatterns([st("a", "pickup"), st("b", "pickup"), st("a", "drop")]))
      expect(p.hint.length).toBeGreaterThan(10);
  });
});
