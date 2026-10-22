/**
 * The single source of truth for "what does the driver do next at this stop".
 * Pure: give it the server's view of the job plus what is on the phone, get back the step,
 * the one primary action, and the progress rail. Every screen reads this; nothing else decides.
 */
import type { PodRequirements } from "../types";
import type { PodDraft } from "./podDraft";
import { podMissing, type PodNeed } from "./podRules";

export type StopKind = "pickup" | "delivery";

export type StopStep =
  | "none" // no current work
  | "offer" // dispatch is waiting for Accept / Decline
  | "off_duty" // accepted work, but the driver is off duty
  | "start" // parcels on board: tap Start delivery (receiver gets "out for delivery")
  | "arrive" // drive there, then tap Arrived
  | "scan" // arrived, packages still to scan
  | "proof" // delivery: proof still missing
  | "complete" // everything done: tap Complete
  | "syncing" // completed on this phone, waiting for signal
  | "waiting"; // state the driver cannot act on (dispatch side)

export type PrimaryAction =
  | "accept"
  | "go_on_duty"
  | "start"
  | "arrive"
  | "scan"
  | "photo"
  | "signature"
  | "id_check"
  | "otp"
  | "complete";

export type RailStep = {
  id: "arrive" | "scan" | "proof" | "done";
  label: string;
  state: "done" | "now" | "todo";
};

export type StopInput = {
  orderState: string | null | undefined;
  stopType: string | null | undefined;
  stopStatus: string | null | undefined;
  hasStop: boolean;
  onDuty: boolean;
  syncing: boolean;
  scanRequired: number;
  scanComplete: boolean;
  pod: PodDraft;
  podRequirements: PodRequirements | null | undefined;
  otpRequired: boolean;
  /** "to_hub": this drop is our warehouse (split order), not the receiver. */
  hubLeg?: string | null;
};

export type StopView = {
  step: StopStep;
  kind: StopKind | null;
  primary: { action: PrimaryAction; label: string } | null;
  podNeeds: PodNeed[];
  rail: RailStep[];
};

const ARRIVE_PICKUP = new Set(["DRIVER_ACCEPTED", "DRIVER_EN_ROUTE"]);
const AT_PICKUP = new Set(["AT_PICKUP"]);
const ARRIVE_DELIVERY = new Set(["PICKED_UP", "IN_TRANSIT"]);
const AT_DELIVERY = new Set(["AT_DESTINATION"]);
const CLOSED = new Set([
  "DELIVERED",
  "POD_COMPLETED",
  "COMPLETED",
  "INVOICED",
  "CLOSED",
  "CANCELLED",
  "CANCELED",
  "FAILED",
  "RETURNED",
  "RETURN_TO_SENDER",
  "DAMAGED",
  "LOST",
  "REFUNDED",
]);

export function normState(state: string | null | undefined): string {
  return (state ?? "").trim().toUpperCase();
}

function stopKind(stopType: string | null | undefined): StopKind | null {
  const t = (stopType ?? "").trim().toLowerCase();
  if (t === "pickup") return "pickup";
  if (t === "delivery" || t === "dropoff" || t === "drop_off") return "delivery";
  return null;
}

export function needsAccept(state: string | null | undefined): boolean {
  return normState(state) === "DRIVER_ASSIGNED";
}

/**
 * Today's "Open stop" button: only when there is something to open — a dispatch-route
 * stop, a stop on the current job, or a new offer to review. A job with no actionable
 * stop gets a "no next stop" note instead of a button that lands on an empty screen.
 */
export function openStopAvailable(input: {
  currentOrderId: string | null | undefined;
  stopId: string | null | undefined;
  orderState: string | null | undefined;
  hasRouteStop: boolean;
}): boolean {
  if (input.hasRouteStop) return true;
  if (!input.currentOrderId) return false;
  return Boolean(input.stopId) || needsAccept(input.orderState);
}

export function isClosed(state: string | null | undefined): boolean {
  return CLOSED.has(normState(state));
}

const POD_ACTION: Record<PodNeed, { action: PrimaryAction; label: string }> = {
  photo_or_signature: { action: "photo", label: "Take delivery photo" },
  photo: { action: "photo", label: "Take delivery photo" },
  signature: { action: "signature", label: "Get signature" },
  id_check: { action: "id_check", label: "Check receiver ID" },
  otp: { action: "otp", label: "Enter receiver code" },
};

export function deriveStop(input: StopInput): StopView {
  const state = normState(input.orderState);
  const kind = stopKind(input.stopType);
  const none: StopView = { step: "none", kind, primary: null, podNeeds: [], rail: [] };

  if (needsAccept(state)) {
    return { ...none, step: "offer", primary: { action: "accept", label: "Accept job" } };
  }
  if (!input.hasStop || !kind || !state || isClosed(state)) return none;

  const arriveSet = kind === "pickup" ? ARRIVE_PICKUP : ARRIVE_DELIVERY;
  const atSet = kind === "pickup" ? AT_PICKUP : AT_DELIVERY;
  if (!arriveSet.has(state) && !atSet.has(state)) {
    return { ...none, step: "waiting" };
  }
  const arrived = atSet.has(state) || (input.stopStatus ?? "").toLowerCase().includes("arriv");
  const needsScan = input.scanRequired > 0;
  const scanned = !needsScan || input.scanComplete;
  const toHub = kind === "delivery" && input.hubLeg === "to_hub";
  const podNeeds =
    kind === "delivery" && !toHub
      ? podMissing(input.pod, input.podRequirements, input.otpRequired)
      : [];

  const railFor = (now: RailStep["id"] | "all_done"): RailStep[] => {
    const ids: Array<{ id: RailStep["id"]; label: string }> = [
      { id: "arrive", label: "Arrive" },
      ...(needsScan ? [{ id: "scan" as const, label: "Scan" }] : []),
      ...(kind === "delivery" && !toHub ? [{ id: "proof" as const, label: "Proof" }] : []),
      { id: "done", label: "Done" },
    ];
    const at = now === "all_done" ? ids.length : ids.findIndex((x) => x.id === now);
    return ids.map((x, i) => ({ ...x, state: i < at ? "done" : i === at ? "now" : "todo" }));
  };

  const view = (
    step: StopStep,
    railNow: RailStep["id"] | "all_done",
    primary: StopView["primary"]
  ) => ({
    step,
    kind,
    primary,
    podNeeds,
    rail: railFor(railNow),
  });

  if (input.syncing) return view("syncing", "all_done", null);
  if (!input.onDuty)
    return view("off_duty", "arrive", { action: "go_on_duty", label: "Go on duty" });
  if (!arrived && toHub) {
    return view("arrive", "arrive", { action: "arrive", label: "Arrived at warehouse" });
  }
  if (!arrived && kind === "delivery" && state === "PICKED_UP") {
    return view("start", "arrive", { action: "start", label: "Start delivery" });
  }
  if (!arrived) {
    return view("arrive", "arrive", {
      action: "arrive",
      label: kind === "pickup" ? "Arrived at pickup" : "Arrived at drop-off",
    });
  }
  if (!scanned) return view("scan", "scan", { action: "scan", label: "Scan packages" });
  if (podNeeds.length) return view("proof", "proof", POD_ACTION[podNeeds[0]]);
  return view("complete", "done", {
    action: "complete",
    label:
      kind === "pickup"
        ? "Picked up — complete"
        : toHub
          ? "Dropped at warehouse — complete"
          : "Delivered — complete",
  });
}
