/**
 * Multi-stop orders (hub & spoke 1->N, multi pickup/drop N->N): every stop comes straight
 * from the assigned order. The first pickup and the final drop drive the order state as on a
 * single job; the stops in between ("{order}-dropoff.{key}") have their own status, so the
 * stop flow reads that status instead of the order state. Pure: no React, no network.
 */
import type { PodRequirements } from "../types";
import type { StopInput } from "./stopFlow";

export type OrderStop = {
  stop_id: string;
  stop_type: string;
  status: string;
  sequence?: number;
  stop_key?: string | null;
  stop_index?: number | null;
  stop_total?: number | null;
  stop_label?: string | null;
  address?: { formatted?: string; lat?: number; lng?: number } | null;
  actions?: string[];
};

/** "o1-dropoff.d2" is a middle stop; "o1-pickup" / "o1-dropoff" are not. */
export function isMidStopId(stopId: string | null | undefined): boolean {
  const tail = (stopId ?? "").split("-").pop() ?? "";
  return tail.includes(".");
}

const MID_DROP_POD: PodRequirements = { enforced: true, photo_or_signature: true };

/**
 * Stop-flow input for the current stop. Middle stops: the stop's own status decides
 * Arrived / Complete (the order is already picked up); one photo or signature per drop,
 * no receiver code (that is for the final drop) and no box scan (scans are per order).
 */
export function stopInputFor(input: StopInput, stopId: string | null | undefined): StopInput {
  if (!isMidStopId(stopId)) return input;
  const arrived = (input.stopStatus ?? "").toLowerCase().includes("arriv");
  const pickup = (input.stopType ?? "").toLowerCase() === "pickup";
  const state = (input.orderState ?? "").toUpperCase();
  const orderState = pickup
    ? arrived
      ? "AT_PICKUP"
      : "DRIVER_EN_ROUTE"
    : arrived
      ? "AT_DESTINATION"
      : state === "PICKED_UP"
        ? "PICKED_UP"
        : "IN_TRANSIT";
  return {
    ...input,
    orderState,
    scanRequired: 0,
    scanComplete: true,
    otpRequired: false,
    podRequirements: pickup ? input.podRequirements : MID_DROP_POD,
  };
}

const STATUS_COPY: Record<string, string> = {
  locked: "Later",
  picked_up: "Picked up",
  delivered: "Delivered",
  arrived: "Arrived",
  at_pickup: "Arrived",
  at_destination: "Arrived",
  in_transit: "On the way",
};

export type StopRow = {
  stopId: string;
  title: string;
  address: string;
  status: string;
  current: boolean;
  done: boolean;
};

/** Rows for the "All stops" list, in order; empty for a plain pickup -> drop job. */
export function orderStopRows(
  stops: OrderStop[] | null | undefined,
  currentStopId: string | null | undefined
): StopRow[] {
  const list = (stops ?? []).filter((s) => s && s.stop_id);
  if (list.length <= 2) return [];
  return list.map((s, i) => {
    const kind = (s.stop_type ?? "").toLowerCase() === "pickup" ? "Pickup" : "Drop-off";
    const status = (s.status ?? "").toLowerCase();
    const done = status === "picked_up" || status === "delivered";
    const current = s.stop_id === currentStopId;
    const label = s.stop_label ? ` · ${s.stop_label}` : "";
    return {
      stopId: s.stop_id,
      title: `${s.stop_index ?? i + 1}. ${kind}${label}`,
      address: s.address?.formatted?.trim() || "Address missing — call dispatch",
      status: current && !done ? "Now" : (STATUS_COPY[status] ?? "Next"),
      current,
      done,
    };
  });
}

/** "Stop 2 of 4" for the header, or null on a plain job. */
export function stopPosition(
  stops: OrderStop[] | null | undefined,
  stopId: string | null
): string | null {
  const list = stops ?? [];
  if (list.length <= 2 || !stopId) return null;
  const i = list.findIndex((s) => s.stop_id === stopId);
  return i < 0 ? null : `Stop ${i + 1} of ${list.length}`;
}
