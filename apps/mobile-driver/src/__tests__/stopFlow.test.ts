import { describe, expect, it } from "vitest";
import { emptyPodDraft } from "../stop/podDraft";
import { deriveStop, type StopInput } from "../stop/stopFlow";

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
