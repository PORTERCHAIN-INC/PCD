import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { midStopIsCurrent, type OrderStop } from "./multi-stops";

const s = (stop_id: string, actions: string[] = [], status = "pending"): OrderStop => ({
  stop_id,
  stop_type: stop_id.endsWith("pickup") ? "pickup" : "drop",
  status,
  actions,
});

describe("L203: Delivery 360 POD waits while a middle stop is open", () => {
  it("is true while the next stop with an action is a middle drop", () => {
    const stops = [
      s("o-pickup", [], "picked_up"),
      s("o-dropoff.pc_stop_2", ["deliver"]),
      s("o-dropoff"),
    ];
    expect(midStopIsCurrent(stops)).toBe(true);
  });
  it("is false once only the final drop is left", () => {
    const stops = [
      s("o-pickup", [], "picked_up"),
      s("o-dropoff.pc_stop_2", [], "delivered"),
      s("o-dropoff", ["deliver"]),
    ];
    expect(midStopIsCurrent(stops)).toBe(false);
  });
  it("Delivery360 hides the signature pad / Complete POD behind midStopIsCurrent", () => {
    const src = readFileSync(join(__dirname, "../components/jobs/Delivery360.tsx"), "utf8");
    expect(src).toMatch(/midStopIsCurrent\(job\.stops\) && \(/);
    expect(src).toMatch(/!midStopIsCurrent\(job\.stops\) && \(/);
  });
});
