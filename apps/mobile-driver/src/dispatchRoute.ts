/** Dispatch route model for the driver app — same rules as the driver portal. */

export type RouteStopKind = "pickup" | "drop" | "return_pickup" | "return_drop" | "hub" | "handoff";
export type CheckinEvent = "arrived" | "picked_up" | "delivered" | "failed";

export type DispatchStop = {
  keys: string[];
  order_id: string;
  order_number: string | null;
  kind: RouteStopKind;
  status: "pending" | "arrived" | "done" | "failed";
  address: string | null;
  lat: number | null;
  lng: number | null;
  boxes: number;
  needs_pod: boolean;
  notes: string | null;
  eta_s: number;
  liftgate?: boolean;
};

export type DispatchRoute = {
  id: string;
  vehicle_class: string;
  stops: DispatchStop[];
  next_index: number | null;
  done: number;
  total: number;
};

export type StopChecklist = {
  items: {
    item_key: string | null;
    label: string;
    box_count: number;
    counts_as: number;
    rule: string | null;
    boxes: { package_id: string }[];
  }[];
  item_count: number;
  box_count: number;
};

export const KIND_LABEL: Record<RouteStopKind, string> = {
  pickup: "Pick up",
  drop: "Deliver",
  return_pickup: "Return pick up",
  return_drop: "Return drop",
  hub: "Hub drop",
  handoff: "Partner handoff",
};

export const isPickup = (k: RouteStopKind) => k === "pickup" || k === "return_pickup";

export function primaryAction(stop: DispatchStop): { event: CheckinEvent; label: string } | null {
  if (stop.status === "done" || stop.status === "failed") return null;
  if (stop.status === "pending") return { event: "arrived", label: "Arrived" };
  return isPickup(stop.kind)
    ? { event: "picked_up", label: "Picked up" }
    : { event: "delivered", label: "Delivered" };
}

export function itemCount(list: StopChecklist | null): number {
  return list ? list.items.reduce((n, it) => n + (it.counts_as || 1), 0) : 0;
}

export const FAIL_REASONS = [
  "Nobody home",
  "Address wrong",
  "Refused",
  "Damaged",
  "Closed",
  "Unsafe",
];
