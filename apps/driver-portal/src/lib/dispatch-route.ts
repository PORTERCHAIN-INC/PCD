/** Committed Dispatch route for the driver + stop check-ins (arrived / picked up / delivered). */

export type RouteStopKind = "pickup" | "drop" | "return_pickup" | "return_drop" | "hub" | "handoff";
export type RouteStopStatus = "pending" | "arrived" | "done" | "failed";
export type CheckinEvent = "arrived" | "picked_up" | "delivered" | "failed";

export interface RouteStop {
  keys: string[];
  order_id: string;
  order_number: string | null;
  kind: RouteStopKind;
  status: RouteStopStatus;
  address: string | null;
  lat: number | null;
  lng: number | null;
  fsa: string | null;
  boxes: number;
  needs_pod: boolean;
  notes: string | null;
  eta_s: number;
  /** Boxes scanned for this stop's phase (pickup or delivery); null at hubs/handoffs. */
  scan: ScanProgress | null;
}

export interface ScanProgress {
  scanned: number;
  required: number;
  complete: boolean;
  missing_suffixes: string[];
  reported_missing?: number;
}

export interface DriverDispatchRoute {
  id: string;
  vehicle_class: string;
  stops: RouteStop[];
  next_index: number | null;
  done: number;
  total: number;
}

export interface ChecklistItem {
  item_key: string | null;
  label: string;
  box_count: number;
  counts_as: number;
  rule: string | null;
  boxes: {
    package_id: string;
    box_index: number;
    tracking_suffix: string;
    scanned: boolean;
    missing: boolean;
  }[];
}

export interface StopChecklist {
  items: ChecklistItem[];
  item_count: number;
  box_count: number;
}

export const PICKUP_KINDS: RouteStopKind[] = ["pickup", "return_pickup"];

export const KIND_LABEL: Record<RouteStopKind, string> = {
  pickup: "Pick up",
  drop: "Deliver",
  return_pickup: "Return pick up",
  return_drop: "Return drop",
  hub: "Hub drop",
  handoff: "Partner handoff",
};

export function isPickup(kind: RouteStopKind): boolean {
  return PICKUP_KINDS.includes(kind);
}

/** The one primary action for a stop. */
export function primaryAction(stop: RouteStop): { event: CheckinEvent; label: string } | null {
  if (stop.status === "done" || stop.status === "failed") return null;
  if (stop.status === "pending") return { event: "arrived", label: "Arrived" };
  return isPickup(stop.kind)
    ? { event: "picked_up", label: "Picked up" }
    : { event: "delivered", label: "Delivered" };
}

/**
 * Offline: apply a queued check-in to the local route so the driver moves on at once.
 * The server's answer replaces this view when the queue syncs.
 */
export function applyLocal(
  route: DriverDispatchRoute,
  keys: string[],
  event: CheckinEvent
): DriverDispatchRoute {
  const key = keys.join(",");
  const stops = route.stops.map((s): RouteStop => {
    if (s.keys.join(",") !== key) return s;
    if (event === "arrived") return { ...s, status: "arrived" };
    return { ...s, status: event === "failed" ? "failed" : "done" };
  });
  const next = stops.findIndex((s) => s.status === "pending" || s.status === "arrived");
  return {
    ...route,
    stops,
    next_index: next === -1 ? null : next,
    done: stops.filter((s) => s.status === "done" || s.status === "failed").length,
  };
}

/** Items to confirm: a multi-box item counts as one item; every box still has to be on the van. */
export function checklistItemCount(list: StopChecklist | null): number {
  if (!list) return 0;
  return list.items.reduce((n, it) => n + (it.counts_as || 1), 0);
}

export function mapsUrl(stop: RouteStop): string | null {
  if (stop.lat == null || stop.lng == null) return null;
  return `https://www.google.com/maps/dir/?api=1&destination=${stop.lat},${stop.lng}`;
}

export function etaClock(seconds: number, from: Date = new Date()): string {
  const d = new Date(from.getTime() + seconds * 1000);
  return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

/** Downscale a camera photo to ≤1280px JPEG so it fits the POD upload limit. */
export async function photoToDataUrl(file: File, max = 1280, quality = 0.6): Promise<string> {
  const raw = await new Promise<string>((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result));
    r.onerror = () => reject(new Error("photo_read_failed"));
    r.readAsDataURL(file);
  });
  const img = await new Promise<HTMLImageElement>((resolve, reject) => {
    const i = new Image();
    i.onload = () => resolve(i);
    i.onerror = () => reject(new Error("photo_decode_failed"));
    i.src = raw;
  });
  const scale = Math.min(1, max / Math.max(img.width, img.height));
  const c = document.createElement("canvas");
  c.width = Math.round(img.width * scale);
  c.height = Math.round(img.height * scale);
  c.getContext("2d")?.drawImage(img, 0, 0, c.width, c.height);
  return c.toDataURL("image/jpeg", quality);
}

export function currentPosition(
  timeoutMs = 5000
): Promise<{ lat: number; lng: number; accuracy_m: number } | null> {
  if (typeof navigator === "undefined" || !navigator.geolocation) return Promise.resolve(null);
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (p) =>
        resolve({ lat: p.coords.latitude, lng: p.coords.longitude, accuracy_m: p.coords.accuracy }),
      () => resolve(null),
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 30_000 }
    );
  });
}
