/**
 * Recipient tracking "experience" payload (GET /v1/orders/{n}/experience) and the
 * signed self-service link (/v1/delivery-manage/{n}). Shared by the website track
 * page and the customer mobile app so both read the same, privacy-safe fields.
 */

export type TrackingStepCode =
  | "booked"
  | "picked_up"
  | "out_for_delivery"
  | "nearby"
  | "delivered"
  | "attempted"
  | "returning"
  | "cancelled"
  | "rescheduled"
  | "instructions";

export interface TrackingTimelineItem {
  code: TrackingStepCode;
  label: string;
  at: string | null;
}

export interface TrackingEtaWindow {
  start: string | null;
  end: string | null;
  label: string | null;
  source: "customer" | "promise" | "booking";
}

export interface TrackingProofOfDelivery {
  delivered_at: string | null;
  proof_types: string[];
  received_by: string | null;
  photos: string[];
}

export interface TrackingExperienceEnhanced {
  enhanced: true;
  tracking_number: string;
  state: string;
  branding: {
    company_name: string | null;
    logo_url: string | null;
    tracking_page_message: string | null;
    primary_color: string | null;
    accent_color: string | null;
  };
  progress: { code: TrackingStepCode; label: string; done: boolean }[];
  timeline: TrackingTimelineItem[];
  eta_window: TrackingEtaWindow | null;
  stops_away: number | null;
  driver: { name: string | null } | null;
  proof_of_delivery: TrackingProofOfDelivery | null;
  attempts: number;
  awaiting_schedule: boolean;
  returning_to_sender: boolean;
  help: { email: string | null; phone: string | null; url: string | null };
  self_service: { available: boolean };
  rules: { id_required: boolean; signature_required: boolean; safe_place_allowed: boolean };
}

export type TrackingExperience =
  { enhanced: false; tracking_number: string } | TrackingExperienceEnhanced;

export interface DeliveryWindowOption {
  code: string;
  date: string;
  wave_code: string;
  window_start: string;
  window_end: string;
  label: string;
}

export interface DeliveryInstructions {
  gate_code?: string | null;
  buzzer?: string | null;
  safe_place?: string | null;
  notes?: string | null;
}

export interface DeliveryManageOptions {
  tracking_number: string;
  state: string;
  can_reschedule: boolean;
  can_edit_instructions: boolean;
  awaiting_schedule: boolean;
  windows: DeliveryWindowOption[];
  schedule: (DeliveryWindowOption & { chosen_at?: string }) | null;
  instructions: DeliveryInstructions & { updated_at?: string };
  rules: { safe_place_allowed: boolean; id_required: boolean; signature_required: boolean };
  attempts: number;
}

const HEX = /^#[0-9a-fA-F]{6}$/;

/** Only a strict #rrggbb colour reaches inline styles; anything else falls back. */
export function safeBrandColor(value: string | null | undefined, fallback = "#1e3a5f"): string {
  return value && HEX.test(value) ? value.toLowerCase() : fallback;
}

export function isEnhancedExperience(
  exp: TrackingExperience | null | undefined
): exp is TrackingExperienceEnhanced {
  return Boolean(exp && exp.enhanced === true);
}

export function stopsAwayText(stops: number | null | undefined, state?: string): string | null {
  if (stops === null || stops === undefined || stops < 0) return null;
  if (state === "AT_DESTINATION") return "Your driver has arrived";
  if (stops === 0) return "You're next";
  return `${stops} stop${stops === 1 ? "" : "s"} before yours`;
}

function fmtTime(d: Date, timeZone: string): string {
  return d
    .toLocaleTimeString("en-CA", { hour: "numeric", minute: "2-digit", timeZone })
    .replace(":00", "")
    .replace(/\s/g, "")
    .replace(/\./g, "")
    .toLowerCase();
}

export function etaWindowText(
  window: TrackingEtaWindow | null | undefined,
  timeZone = "America/Toronto"
): string | null {
  if (!window) return null;
  if (window.label) return window.label;
  if (!window.start) return null;
  const start = new Date(window.start);
  if (Number.isNaN(start.getTime())) return null;
  const day = start.toLocaleDateString("en-CA", {
    weekday: "short",
    month: "short",
    day: "numeric",
    timeZone,
  });
  if (!window.end) return `${day}, from ${fmtTime(start, timeZone)}`;
  const end = new Date(window.end);
  if (Number.isNaN(end.getTime())) return `${day}, from ${fmtTime(start, timeZone)}`;
  return `${day}, ${fmtTime(start, timeZone)}-${fmtTime(end, timeZone)}`;
}

export function statusHeadline(exp: TrackingExperienceEnhanced): string {
  if (exp.returning_to_sender) return "Returning to sender";
  if (exp.awaiting_schedule) return "Choose a delivery time";
  switch (exp.state) {
    case "DELIVERED":
    case "POD_COMPLETED":
    case "INVOICED":
    case "CLOSED":
      return "Delivered";
    case "AT_DESTINATION":
      return "Your driver has arrived";
    case "IN_TRANSIT":
      return exp.stops_away === 0 ? "You're next" : "Out for delivery";
    case "PICKED_UP":
      return "Picked up";
    case "FAILED":
      return "Delivery attempted";
    case "CANCELLED":
      return "Cancelled";
    default:
      return "Order received";
  }
}

const MANAGE_ERRORS: Record<string, string> = {
  link_invalid: "This link is not valid. Use the latest link we sent you.",
  link_expired: "This link has expired. Use the latest link we sent you.",
  self_service_disabled: "Online delivery changes are not available for this sender.",
  reschedule_closed: "This delivery can no longer be rescheduled online.",
  instructions_closed: "Instructions can no longer be changed for this delivery.",
  window_unavailable: "That delivery window is no longer available. Pick another.",
  safe_place_not_allowed:
    "This sender requires a hand-to-hand delivery, so a safe place cannot be used.",
};

export function manageErrorText(code: string | null | undefined): string {
  return (code && MANAGE_ERRORS[code]) || "Something went wrong. Please try again.";
}

/** Trim and drop empty instruction fields (and safe place when the sender forbids it). */
export function cleanInstructions(
  input: DeliveryInstructions,
  rules: { safe_place_allowed: boolean }
): DeliveryInstructions {
  const out: DeliveryInstructions = {};
  for (const key of ["gate_code", "buzzer", "safe_place", "notes"] as const) {
    const value = (input[key] ?? "").trim();
    if (!value) continue;
    if (key === "safe_place" && !rules.safe_place_allowed) continue;
    out[key] = value;
  }
  return out;
}
