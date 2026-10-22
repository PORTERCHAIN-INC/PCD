import { describe, expect, it, vi } from "vitest";
import {
  isMidStopId,
  orderStopRows,
  stopInputFor,
  stopPosition,
  type OrderStop,
} from "../stop/multiStop";
import { emptyPodDraft } from "../stop/podDraft";
import { deriveStop, type StopInput } from "../stop/stopFlow";

vi.mock("../api", () => ({
  deliverStop: vi.fn(async () => ({})),
  podComplete: vi.fn(async () => ({})),
  podIdCheck: vi.fn(async () => ({})),
  podPhoto: vi.fn(async () => ({})),
  podSignature: vi.fn(async () => ({})),
}));
vi.mock("../offline", () => ({
  runOnlineOrQueue: async (_t: string, _p: unknown, fn: () => Promise<unknown>) => {
    await fn();
    return "online";
  },
}));

const base = (over: Partial<StopInput> = {}): StopInput => ({
  orderState: "PICKED_UP",
  stopType: "dropoff",
  stopStatus: "pending",
  hasStop: true,
  onDuty: true,
  syncing: false,
  scanRequired: 2,
  scanComplete: false,
  pod: emptyPodDraft(),
  podRequirements: { enforced: true, photo: true, signature: true },
  otpRequired: true,
  ...over,
});

const HUB_SPOKE: OrderStop[] = [
  { stop_id: "o1-pickup", stop_type: "pickup", status: "picked_up", stop_index: 1 },
  {
    stop_id: "o1-dropoff.d1",
    stop_type: "dropoff",
    status: "pending",
    stop_index: 2,
    address: { formatted: "2 Sheppard Ave E" },
  },
  {
    stop_id: "o1-dropoff.d2",
    stop_type: "dropoff",
    status: "locked",
    stop_index: 3,
    address: { formatted: "" },
  },
  { stop_id: "o1-dropoff", stop_type: "dropoff", status: "locked", stop_index: 4 },
];

describe("multi-stop orders on the phone", () => {
  it("tells middle stops from the first pickup / final drop", () => {
    expect(isMidStopId("o1-dropoff.d1")).toBe(true);
    expect(isMidStopId("ab-cd-pickup.pb")).toBe(true);
    expect(isMidStopId("o1-dropoff")).toBe(false);
    expect(isMidStopId(null)).toBe(false);
  });

  it("first middle drop after pickup: Start delivery, then Arrived, then one proof", () => {
    const start = deriveStop(stopInputFor(base(), "o1-dropoff.d1"));
    expect(start.primary?.action).toBe("start");
    const arrive = deriveStop(stopInputFor(base({ orderState: "IN_TRANSIT" }), "o1-dropoff.d2"));
    expect(arrive.primary?.action).toBe("arrive");
    const proof = deriveStop(
      stopInputFor(base({ orderState: "IN_TRANSIT", stopStatus: "arrived" }), "o1-dropoff.d2")
    );
    expect(proof.step).toBe("proof"); // no box scan, no receiver code at a middle drop
    expect(proof.primary?.action).toBe("photo");
    const done = deriveStop(
      stopInputFor(
        base({
          orderState: "IN_TRANSIT",
          stopStatus: "arrived",
          pod: { ...emptyPodDraft(), photoUrl: "data:x" },
        }),
        "o1-dropoff.d2"
      )
    );
    expect(done.primary?.action).toBe("complete");
  });

  it("a second pickup works while the order is already picked up", () => {
    const v = deriveStop(
      stopInputFor(base({ stopType: "pickup", orderState: "PICKED_UP" }), "o1-pickup.pb")
    );
    expect(v.primary).toEqual({ action: "arrive", label: "Arrived at pickup" });
    const at = deriveStop(
      stopInputFor(base({ stopType: "pickup", stopStatus: "arrived" }), "o1-pickup.pb")
    );
    expect(at.primary?.action).toBe("complete");
  });

  it("the final drop keeps the order's own rules", () => {
    const input = base({ orderState: "AT_DESTINATION" });
    expect(stopInputFor(input, "o1-dropoff")).toBe(input);
  });

  it("lists every stop in order with where the driver is", () => {
    const rows = orderStopRows(HUB_SPOKE, "o1-dropoff.d1");
    expect(rows.map((r) => r.title)).toEqual([
      "1. Pickup",
      "2. Drop-off",
      "3. Drop-off",
      "4. Drop-off",
    ]);
    expect(rows.map((r) => r.status)).toEqual(["Picked up", "Now", "Later", "Later"]);
    expect(rows[2].address).toBe("Address missing — call dispatch");
    expect(stopPosition(HUB_SPOKE, "o1-dropoff.d1")).toBe("Stop 2 of 4");
    expect(orderStopRows(HUB_SPOKE.slice(0, 2), null)).toEqual([]);
  });

  it("completing a middle drop sends its proof and the stop, not pod_complete", async () => {
    const api = await import("../api");
    const { completeStop } = await import("../stop/completeStop");
    await completeStop({
      routeId: "r1",
      stopId: "o1-dropoff.d1",
      kind: "delivery",
      otpRequired: false,
      podRequirements: { enforced: true, photo_or_signature: true },
      pod: { ...emptyPodDraft(), photoUrl: "data:x" },
      midStop: true,
    });
    expect(api.podPhoto).toHaveBeenCalledWith("r1", "o1-dropoff.d1", "data:x");
    expect(api.podComplete).not.toHaveBeenCalled();
    expect(api.deliverStop).toHaveBeenCalledWith("r1", "o1-dropoff.d1");
  });
});
