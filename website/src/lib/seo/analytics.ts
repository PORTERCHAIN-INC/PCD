/**
 * Analytics instrumentation. Event names and properties aligned with taxonomy.
 * Merge attribution (sourcePage, sourceSection, locale, landingPageUrl, referrer, UTM) into every event.
 * Plug in gtag, Segment, or custom endpoint via setAnalyticsProvider().
 */

import { getStoredAttribution, type Attribution } from "./attribution";

export type AnalyticsEventProperties = Record<string, string | number | boolean | undefined>;

let provider: ((event: string, properties: Record<string, unknown>) => void) | null = null;

/**
 * Set the analytics provider (e.g. gtag, Segment track). Call from layout or _app.
 * If never set, events are no-ops (or use console in dev).
 */
export function setAnalyticsProvider(
  fn: (event: string, properties: Record<string, unknown>) => void
): void {
  provider = fn;
}

/**
 * Track an event with optional properties. Attribution is merged automatically.
 */
export function track(eventName: string, properties: AnalyticsEventProperties = {}): void {
  const att = getStoredAttribution();
  const payload: Record<string, unknown> = {
    ...att,
    ...Object.fromEntries(Object.entries(properties).filter(([, v]) => v !== undefined)),
  };
  if (provider) {
    provider(eventName, payload);
  } else if (typeof window !== "undefined" && process.env.NODE_ENV === "development") {
    console.debug("[analytics]", eventName, payload);
  }
}

/** Event names (taxonomy) */
export const ANALYTICS_EVENTS = {
  /** Homepage / CTA */
  CTA_CLICK: "cta_click",
  /** Merchant wizard */
  MERCHANT_WIZARD_STEP_VIEW: "merchant_wizard_step_view",
  MERCHANT_WIZARD_SUBMIT_SUCCESS: "merchant_wizard_submit_success",
  MERCHANT_WIZARD_SUBMIT_ERROR: "merchant_wizard_submit_error",
  /** Driver application */
  DRIVER_APPLICATION_STEP_VIEW: "driver_application_step_view",
  DRIVER_APPLICATION_SUBMIT_SUCCESS: "driver_application_submit_success",
  DRIVER_APPLICATION_SUBMIT_ERROR: "driver_application_submit_error",
  /** Tracking */
  TRACKING_LOOKUP: "tracking_lookup",
  TRACKING_LOOKUP_SUCCESS: "tracking_lookup_success",
  TRACKING_LOOKUP_NOT_FOUND: "tracking_lookup_not_found",
  TRACKING_LOOKUP_ERROR: "tracking_lookup_error",
  /** Support issue */
  SUPPORT_ISSUE_SUBMIT_SUCCESS: "support_issue_submit_success",
  SUPPORT_ISSUE_SUBMIT_ERROR: "support_issue_submit_error",
  /** Contact page form */
  CONTACT_FORM_SUBMIT_SUCCESS: "contact_form_submit_success",
  CONTACT_FORM_SUBMIT_ERROR: "contact_form_submit_error",
  /** Demo request (legacy / ops pages only) */
  DEMO_REQUEST: "demo_request",
  /** Quote / transportation capacity request */
  QUOTE_REQUEST: "quote_request",
  /** Platform bridge on Lane B SEO pages */
  SEO_BRIDGE_CLICK: "seo_bridge_click",
  PLATFORM_EXPLORE: "platform_explore",
  /** Booking widget (homepage / book flow) */
  BOOKING_QUOTE_REQUEST: "booking_quote_request",
  BOOKING_QUOTE_SUCCESS: "booking_quote_success",
  BOOKING_CONTINUE: "booking_continue",
  /** Business page inquiry */
  BUSINESS_INQUIRY_SUBMIT: "business_inquiry_submit",
  /** Zoho SalesIQ */
  ZOHO_CHAT_READY: "zoho_chat_ready",
  ZOHO_CHAT_OPEN: "zoho_chat_open",
  /** Google Business Profile */
  GBP_PROFILE_CLICK: "gbp_profile_click",
  GBP_REVIEW_CLICK: "gbp_review_click",
} as const;

/** Mark these as conversions in GA4 Admin → Events → Mark as conversion. */
export const GA4_CONVERSION_EVENTS: readonly string[] = [
  ANALYTICS_EVENTS.CONTACT_FORM_SUBMIT_SUCCESS,
  ANALYTICS_EVENTS.DEMO_REQUEST,
  ANALYTICS_EVENTS.QUOTE_REQUEST,
  ANALYTICS_EVENTS.BUSINESS_INQUIRY_SUBMIT,
  ANALYTICS_EVENTS.BOOKING_QUOTE_SUCCESS,
  ANALYTICS_EVENTS.BOOKING_CONTINUE,
  ANALYTICS_EVENTS.ZOHO_CHAT_OPEN,
  ANALYTICS_EVENTS.GBP_REVIEW_CLICK,
];
