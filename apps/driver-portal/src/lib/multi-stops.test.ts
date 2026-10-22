import { describe, expect, it } from "vitest";
import {
  currentStop,
  isMidStopId,
  midStopButtons,
  midStopIsCurrent,
  stopAddress,
  stopStatusLabel,
  stopTitle,
  type OrderStop,
} from "./multi-stops";

const hubSpoke = (over: Partial<Record<number, Partial<OrderStop>>> = {}): OrderStop[] =>
  [
    { stop_id: "o-1-pickup", stop_type: "pickup", status: "picked_up", actions: [] },
    {
      stop_id: "o-1-dropoff.d1",
      stop_type: "dropoff",
      status: "pending",
      stop_label: "Unit 4",
      actions: ["start_delivery", "arrive", "complete"],
      address: { formatted: "2 Sheppard Ave E" },
    },
    { stop_id: "o-1-dropoff.d2", stop_type: "dropoff", status: "locked", actions: [] },
    { stop_id: "o-1-dropoff", stop_type: "dropoff", status: "locked", actions: [] },
  ].map((s, i) => ({ ...s, ...(over[i] ?? {}) }));

describe("multi-stop orders in the driver portal", () => {
  it("knows middle stops from the first pickup and final drop", () => {
    expect(isMidStopId("o-1-dropoff.d1")).toBe(true);
    expect(isMidStopId("o-1-dropoff")).toBe(false);
    expect(isMidStopId(undefined)).toBe(false);
  });

  it("the current middle drop gets Start / Arrived / Delivered and hides the main button", () => {
    const stops = hubSpoke();
    expect(currentStop(stops)?.stop_id).toBe("o-1-dropoff.d1");
    expect(midStopIsCurrent(stops)).toBe(true);
    expect(midStopButtons(stops[1]).map((b) => b.key)).toEqual([
      "start_delivery",
      "arrive",
      "complete",
    ]);
    expect(midStopButtons(stops[2])).toEqual([]); // locked: later
    expect(stopTitle(stops[1], 1)).toBe("2. Drop-off · Unit 4");
    expect(stopStatusLabel(stops[2].status)).toBe("Later");
    expect(stopAddress(stops[2])).toBe("Address missing — call dispatch");
  });

  it("the final drop goes back to the normal Delivery 360 flow", () => {
    const stops = hubSpoke({
      1: { status: "delivered", actions: [] },
      2: { status: "delivered", actions: [] },
      3: { status: "in_transit", actions: ["arrive", "complete"] },
    });
    expect(currentStop(stops)?.stop_id).toBe("o-1-dropoff");
    expect(midStopIsCurrent(stops)).toBe(false);
    expect(midStopButtons(stops[3])).toEqual([]);
  });

  it("a plain pickup -> drop job is not multi-stop", () => {
    expect(midStopIsCurrent(hubSpoke().slice(0, 2))).toBe(false);
    expect(midStopIsCurrent(undefined)).toBe(false);
  });
});
