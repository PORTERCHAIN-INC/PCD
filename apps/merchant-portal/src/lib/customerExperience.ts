/** Merchant settings for the recipient experience (GET/PUT /v1/merchant/settings/customer-experience). */

export type CxChannel = "email" | "sms" | "whatsapp";
export type CxEvent =
  | "out_for_delivery"
  | "next_stop"
  | "eta_20"
  | "delivered"
  | "attempted"
  | "schedule_request"
  | "rescheduled";
export type CxLanguage = "auto" | "en" | "fr";

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
    /** Receiver email language: auto = recipient's language, else Quebec drop-off -> French. */
    language: CxLanguage;
    /** Per-recipient rate limit for "minutes away" / "you're next" emails (0 = off). */
    eta_min_interval_minutes: number;
    /** Email button colour; only used when white text on it passes WCAG AA (4.5:1). */
    brand_color?: string | null;
    /** https logo for the email header; empty = logo from Branding settings. */
    logo_url?: string | null;
    /** Where recipient replies go (your support inbox). */
    reply_to?: string | null;
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
  rescheduled: "New delivery time confirmed",
};

export const CX_LANGUAGE_LABELS: Record<CxLanguage, string> = {
  auto: "Automatic (French for Quebec or French-speaking recipients)",
  en: "English",
  fr: "French",
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
  const n = s.notifications;
  if (n.brand_color && !/^#[0-9a-fA-F]{6}$/.test(n.brand_color))
    return "Brand colour must look like #0f766e.";
  if (n.logo_url && !n.logo_url.startsWith("https://"))
    return "The logo link must start with https://";
  if (n.reply_to && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(n.reply_to))
    return "The reply-to email does not look valid.";
  if (n.eta_min_interval_minutes < 0 || n.eta_min_interval_minutes > 240) {
    return "The 'close by' limit must be between 0 and 240 minutes.";
  }
  if (s.reattempt.max_attempts < 1 || s.reattempt.max_attempts > 5) {
    return "Delivery attempts must be between 1 and 5.";
  }
  return null;
}

/** WCAG contrast of white text on a hex colour (email button). AA needs 4.5. */
export function contrastOnWhite(hex: string): number {
  const m = /^#([0-9a-f]{6})$/i.exec(hex);
  if (!m) return 0;
  const ch = (i: number) => {
    const c = parseInt(m[1].slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  const lum = 0.2126 * ch(0) + 0.7152 * ch(2) + 0.0722 * ch(4);
  return 1.05 / (lum + 0.05);
}
