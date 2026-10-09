/** Merchant settings for the recipient experience (GET/PUT /v1/merchant/settings/customer-experience). */

export type CxChannel = "email" | "sms" | "whatsapp";
export type CxEvent =
  "out_for_delivery" | "next_stop" | "eta_20" | "delivered" | "attempted" | "schedule_request";

export type CustomerExperienceSettings = {
  tracking: {
    branded_page: boolean;
    show_driver_first_name: boolean;
    show_stops_away: boolean;
    show_pod_photo: boolean;
    support_email: string | null;
    support_phone: string | null;
    help_url: string | null;
  };
  notifications: {
    enabled: boolean;
    channels: Record<CxChannel, boolean>;
    events: Record<CxEvent, boolean>;
    next_stop_threshold: number;
    eta_minutes: number;
    quiet_hours: { enabled: boolean; start: string; end: string; timezone: string };
  };
  self_service: {
    enabled: boolean;
    link_ttl_hours: number;
    allow_reschedule: boolean;
    allow_instructions: boolean;
    schedule_days: number;
  };
  delivery_rules: {
    safe_place_allowed: boolean;
    id_required: boolean;
    signature_required: boolean;
    require_schedule_for_bulky: boolean;
    bulky_package_types: string[];
    bulky_vehicle_classes: string[];
  };
  reattempt: { enabled: boolean; max_attempts: number; return_to_sender_after: number };
};

export type CustomerExperienceResponse = {
  settings: CustomerExperienceSettings;
  presets: string[];
};

export const CX_EVENT_LABELS: Record<CxEvent, string> = {
  out_for_delivery: "Out for delivery",
  next_stop: "You're next / N stops away",
  eta_20: "Driver about N minutes away",
  delivered: "Delivered (with proof-of-delivery link)",
  attempted: "Delivery attempted (with reschedule link)",
  schedule_request: "Choose a delivery time (bulky items)",
};

export const CX_PRESET_LABELS: Record<string, string> = {
  pharmacy: "Pharmacy: no safe place, ID + signature required",
  furniture: "Furniture / bulky: recipient picks a time before dispatch",
};

/** Plain-language list of what recipients will actually see with these settings. */
export function cxCustomerFacingSummary(s: CustomerExperienceSettings): string[] {
  const out: string[] = [];
  if (s.tracking.branded_page) out.push("Branded tracking page with your logo and colours");
  if (s.notifications.enabled) {
    const channels = (["email", "sms"] as const).filter((c) => s.notifications.channels[c]);
    const events = (Object.keys(CX_EVENT_LABELS) as CxEvent[]).filter(
      (e) => s.notifications.events[e]
    );
    if (channels.length && events.length) {
      out.push(`${events.length} delivery update(s) by ${channels.join(" + ")}`);
    }
  }
  if (s.self_service.enabled)
    out.push("Recipients can reschedule and add gate codes via a secure link");
  if (s.delivery_rules.require_schedule_for_bulky && s.self_service.enabled) {
    out.push("Bulky orders wait for the recipient to pick a time before dispatch");
  }
  if (s.reattempt.enabled) {
    out.push(
      `Failed deliveries: up to ${s.reattempt.max_attempts} attempt(s), return to sender after ${s.reattempt.return_to_sender_after}`
    );
  }
  return out;
}

/** Client-side checks mirroring the API so the form explains problems before saving. */
export function cxValidationError(s: CustomerExperienceSettings): string | null {
  const hhmm = /^([01]\d|2[0-3]):([0-5]\d)$/;
  const qh = s.notifications.quiet_hours;
  if (!hhmm.test(qh.start) || !hhmm.test(qh.end)) return "Quiet hours must look like 21:00.";
  if (s.tracking.help_url && !s.tracking.help_url.startsWith("https://")) {
    return "The help link must start with https://";
  }
  if (s.tracking.support_email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(s.tracking.support_email)) {
    return "The support email does not look valid.";
  }
  if (s.notifications.eta_minutes < 5 || s.notifications.eta_minutes > 120) {
    return "The 'minutes away' alert must be between 5 and 120 minutes.";
  }
  if (s.reattempt.max_attempts < 1 || s.reattempt.max_attempts > 5) {
    return "Delivery attempts must be between 1 and 5.";
  }
  return null;
}
