/**
 * Delivery options — one shared set for every booking surface (merchant portal, customer web,
 * customer app, admin, Shopify), the driver apps and the thermal label.
 * Python twin: apps/api/src/porterchain_api/domain/delivery_options.py (keep keys in step).
 * Sent as `dropoff.delivery_options` (admin: top-level `delivery_options`).
 */

export type DropMethod = "leave_at_door" | "hand_to_recipient" | "concierge";

export type DeliveryOptions = {
  drop_method?: DropMethod | null;
  call_on_arrival?: boolean;
  load_help?: boolean;
  unit?: string | null;
  buzzer?: string | null;
  note?: string | null;
};

export const DROP_METHODS: ReadonlyArray<{ id: DropMethod; label: string; hint: string }> = [
  { id: "leave_at_door", label: "Leave at door", hint: "Safe drop, photo taken" },
  { id: "hand_to_recipient", label: "Hand to recipient only", hint: "No safe drop" },
  { id: "concierge", label: "Leave with concierge / reception", hint: "Front desk or lobby" },
];

export const DELIVERY_FLAGS: ReadonlyArray<{
  id: "call_on_arrival" | "load_help";
  label: string;
}> = [
  { id: "call_on_arrival", label: "Call on arrival" },
  { id: "load_help", label: "Needs help loading / unloading" },
];

export const DELIVERY_TEXT_LIMITS = { unit: 40, buzzer: 40, note: 500 } as const;

const clean = (v: unknown, limit: number): string | undefined => {
  const s = String(v ?? "")
    .split(/\s+/)
    .filter(Boolean)
    .join(" ")
    .slice(0, limit);
  return s || undefined;
};

/** Same rules as the API: unknown drop methods and blank text are dropped; empty → undefined. */
export function normalizeDeliveryOptions(
  raw: DeliveryOptions | null | undefined
): DeliveryOptions | undefined {
  if (!raw) return undefined;
  const out: DeliveryOptions = {};
  if (raw.drop_method && DROP_METHODS.some((m) => m.id === raw.drop_method)) {
    out.drop_method = raw.drop_method;
  }
  if (raw.call_on_arrival) out.call_on_arrival = true;
  if (raw.load_help) out.load_help = true;
  for (const key of ["unit", "buzzer", "note"] as const) {
    const v = clean(raw[key], DELIVERY_TEXT_LIMITS[key]);
    if (v) out[key] = v;
  }
  return Object.keys(out).length ? out : undefined;
}

/** Short review lines ("Leave at door", "Unit 4", "Buzzer 12", …). */
export function deliveryOptionLines(raw: DeliveryOptions | null | undefined): string[] {
  const o = normalizeDeliveryOptions(raw);
  if (!o) return [];
  const lines: string[] = [];
  const m = DROP_METHODS.find((d) => d.id === o.drop_method);
  if (m) lines.push(m.label);
  if (o.unit) lines.push(`Unit ${o.unit}`);
  if (o.buzzer) lines.push(`Buzzer ${o.buzzer}`);
  for (const f of DELIVERY_FLAGS) if (o[f.id]) lines.push(f.label);
  if (o.note) lines.push(o.note);
  return lines;
}
