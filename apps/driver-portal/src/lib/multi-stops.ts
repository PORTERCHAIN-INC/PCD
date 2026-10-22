/**
 * Multi-stop orders (hub & spoke 1->N, multi pickup/drop N->N) in the driver portal.
 * The job detail lists every stop in plan order with what the driver can do there now.
 * The first pickup ("{order}-pickup") and the final drop ("{order}-dropoff") keep the
 * normal Delivery 360 flow; stops in between ("{order}-dropoff.{key}") are worked here.
 */
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

export function isMidStopId(stopId: string | null | undefined): boolean {
  return (stopId ?? "").split("-").pop()?.includes(".") ?? false;
}

export function isMultiStop(stops: OrderStop[] | null | undefined): boolean {
  return (stops ?? []).length > 2;
}

/** The stop the driver works now: the first one with an action. */
export function currentStop(stops: OrderStop[] | null | undefined): OrderStop | null {
  return (stops ?? []).find((s) => (s.actions ?? []).length > 0) ?? null;
}

/** True when the current stop is a middle stop, so Delivery 360's own button must wait. */
export function midStopIsCurrent(stops: OrderStop[] | null | undefined): boolean {
  return isMultiStop(stops) && isMidStopId(currentStop(stops)?.stop_id);
}

const STATUS: Record<string, string> = {
  locked: "Later",
  picked_up: "Picked up",
  delivered: "Delivered",
  arrived: "Arrived",
  at_pickup: "Arrived",
  at_destination: "Arrived",
  in_transit: "On the way",
  pending: "Next",
};

export function stopStatusLabel(status: string | null | undefined): string {
  const s = (status ?? "").toLowerCase();
  return STATUS[s] ?? (s ? s.replace(/_/g, " ") : "—");
}

export function stopTitle(stop: OrderStop, index: number): string {
  const kind = stop.stop_type === "pickup" ? "Pickup" : "Drop-off";
  return `${stop.stop_index ?? index + 1}. ${kind}${stop.stop_label ? ` · ${stop.stop_label}` : ""}`;
}

export function stopAddress(stop: OrderStop): string {
  return stop.address?.formatted?.trim() || "Address missing — call dispatch";
}

export type StopButton = { key: "start_delivery" | "arrive" | "complete"; label: string };

/** Buttons for a middle stop (the backend's per-stop actions, worded for the driver). */
export function midStopButtons(stop: OrderStop): StopButton[] {
  if (!isMidStopId(stop.stop_id)) return [];
  const drop = stop.stop_type !== "pickup";
  const actions = stop.actions ?? [];
  const out: StopButton[] = [];
  if (actions.includes("start_delivery"))
    out.push({ key: "start_delivery", label: "Start Delivery" });
  if (actions.includes("arrive"))
    out.push({ key: "arrive", label: drop ? "Arrived at Drop-off" : "Arrived at Pickup" });
  if (actions.includes("complete"))
    out.push({ key: "complete", label: drop ? "Delivered" : "Picked Up" });
  return out;
}
