import { describe, expect, it } from "vitest";
import { emptyPodDraft } from "../stop/podDraft";
import { deriveStop, openStopAvailable, type StopInput } from "../stop/stopFlow";

const base = (over: Partial<StopInput> = {}): StopInput => ({
  orderState: "DRIVER_ACCEPTED",
  stopType: "pickup",
  stopStatus: "pending",
  hasStop: true,
  onDuty: true,
  syncing: false,
  scanRequired: 0,
  scanComplete: false,
  pod: emptyPodDraft(),
  podRequirements: { enforced: true, photo_or_signature: true },
  otpRequired: false,
  ...over,
});

const primary = (over: Partial<StopInput>) => deriveStop(base(over)).primary?.action ?? null;

describe("deriveStop — one primary action per step", () => {
  it("offer → Accept, even before a stop exists", () => {
    const v = deriveStop(base({ orderState: "DRIVER_ASSIGNED", hasStop: false }));
    expect(v.step).toBe("offer");
    expect(v.primary?.action).toBe("accept");
  });

  it("no job / closed job → nothing to do", () => {
    expect(deriveStop(base({ orderState: null, hasStop: false })).step).toBe("none");
    expect(deriveStop(base({ orderState: "DELIVERED" })).step).toBe("none");
    expect(deriveStop(base({ orderState: "POD_COMPLETED", stopType: "delivery" })).step).toBe(
      "none"
    );
  });

  it("off duty → Go on duty, before anything else", () => {
    expect(primary({ onDuty: false })).toBe("go_on_duty");
  });

  it("pickup: Arrive → Scan → Complete", () => {
    expect(primary({ scanRequired: 2 })).toBe("arrive");
    expect(primary({ orderState: "AT_PICKUP", scanRequired: 2 })).toBe("scan");
    expect(primary({ orderState: "AT_PICKUP", scanRequired: 2, scanComplete: true })).toBe(
      "complete"
    );
    expect(primary({ stopStatus: "arrived", scanRequired: 0 })).toBe("complete");
  });

  it("pickup never asks for proof of delivery", () => {
    const v = deriveStop(base({ orderState: "AT_PICKUP" }));
    expect(v.podNeeds).toEqual([]);
    expect(v.rail.map((r) => r.id)).toEqual(["arrive", "done"]);
  });

  it("delivery: Arrive → Proof (server policy order) → Complete", () => {
    const d = { stopType: "delivery", orderState: "IN_TRANSIT" };
    expect(primary(d)).toBe("arrive");
    const at = { ...d, orderState: "AT_DESTINATION" };
    expect(primary(at)).toBe("photo");
    expect(primary({ ...at, pod: { ...emptyPodDraft(), signature: "sig" } })).toBe("complete");
    const strict = {
      ...at,
      podRequirements: { enforced: true, photo: true, signature: true, id_check: true },
      otpRequired: true,
    };
    expect(primary(strict)).toBe("photo");
    expect(primary({ ...strict, pod: { ...emptyPodDraft(), photoUrl: "p" } })).toBe("signature");
    expect(primary({ ...strict, pod: { ...emptyPodDraft(), photoUrl: "p", signature: "s" } })).toBe(
      "id_check"
    );
    expect(
      primary({
        ...strict,
        pod: {
          ...emptyPodDraft(),
          photoUrl: "p",
          signature: "s",
          idType: "passport",
          idNameMatches: true,
        },
      })
    ).toBe("otp");
  });

  it("follows the server when it does not enforce POD", () => {
    expect(
      primary({
        stopType: "delivery",
        orderState: "AT_DESTINATION",
        podRequirements: { enforced: false },
      })
    ).toBe("complete");
  });

  it("queued completion shows 'syncing' with no action — never a second Complete", () => {
    const v = deriveStop(
      base({ stopType: "delivery", orderState: "AT_DESTINATION", syncing: true })
    );
    expect(v.step).toBe("syncing");
    expect(v.primary).toBeNull();
    expect(v.rail.every((r) => r.state === "done")).toBe(true);
  });

  it("states the driver cannot act on → waiting", () => {
    expect(deriveStop(base({ orderState: "PICKED_UP" })).step).toBe("waiting");
  });

  it("rail marks exactly one step as now", () => {
    const v = deriveStop(base({ orderState: "AT_PICKUP", scanRequired: 1 }));
    expect(v.rail.filter((r) => r.state === "now").map((r) => r.id)).toEqual(["scan"]);
    expect(v.rail[0].state).toBe("done");
  });
});

describe("delivery after pickup (ORD-20261015-71FB4B regression)", () => {
  it("picked up + delivery stop → Start delivery, rail on Arrive", () => {
    const v = deriveStop(base({ stopType: "dropoff", orderState: "PICKED_UP" }));
    expect(v.step).toBe("start");
    expect(v.kind).toBe("delivery");
    expect(v.primary).toEqual({ action: "start", label: "Start delivery" });
    expect(v.rail.find((r) => r.state === "now")?.id).toBe("arrive");
  });

  it("after Start delivery (in transit) → Arrived at drop-off", () => {
    expect(primary({ stopType: "dropoff", orderState: "IN_TRANSIT" })).toBe("arrive");
  });

  it("off duty still asks to go on duty first", () => {
    expect(primary({ stopType: "delivery", orderState: "PICKED_UP", onDuty: false })).toBe(
      "go_on_duty"
    );
  });
});

describe("openStopAvailable — never 'Open stop' with nothing behind it", () => {
  const job = { currentOrderId: "o1", stopId: null, orderState: "PICKED_UP", hasRouteStop: false };
  it("job without a stop → no button", () => {
    expect(openStopAvailable(job)).toBe(false);
  });
  it("job with a stop → button", () => {
    expect(openStopAvailable({ ...job, stopId: "o1-dropoff" })).toBe(true);
  });
  it("new offer → button (review), even before a stop exists", () => {
    expect(openStopAvailable({ ...job, orderState: "DRIVER_ASSIGNED" })).toBe(true);
  });
  it("dispatch route stop → button; nothing at all → no button", () => {
    expect(openStopAvailable({ ...job, currentOrderId: null, hasRouteStop: true })).toBe(true);
    expect(openStopAvailable({ ...job, currentOrderId: null })).toBe(false);
  });
});

describe("deriveStop — warehouse split (pickup leg ends at our hub)", () => {
  const hub = (over: Partial<StopInput> = {}) =>
    deriveStop(
      base({
        orderState: "PICKED_UP",
        stopType: "dropoff",
        hubLeg: "to_hub",
        otpRequired: true,
        ...over,
      })
    );

  it("goes straight to Arrived at warehouse, no Start delivery", () => {
    const v = hub();
    expect(v.primary).toEqual({ action: "arrive", label: "Arrived at warehouse" });
    expect(v.rail.map((r) => r.id)).not.toContain("proof");
  });

  it("no receiver code or photo at the hub", () => {
    const v = hub({ stopStatus: "arrived" });
    expect(v.podNeeds).toEqual([]);
    expect(v.primary?.label).toBe("Dropped at warehouse — complete");
  });

  it("delivery leg from the hub is a normal delivery", () => {
    const v = deriveStop(base({ orderState: "PICKED_UP", stopType: "dropoff", hubLeg: "at_hub" }));
    expect(v.primary?.action).toBe("start");
  });
});
