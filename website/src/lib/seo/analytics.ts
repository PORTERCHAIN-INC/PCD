/**
 * Analytics instrumentation. Event names and properties aligned with taxonomy.
 * Merge attribution (sourcePage, sourceSection, locale, landingPageUrl, referrer, UTM) into every event.
 * Plug in gtag, Segment, or custom endpoint via setAnalyticsProvider().
 */

import { getStoredAttribution, type Attribution } from "./attribution";

export type AnalyticsEventProperties = Record<string, string | number | boolean | undefined>;

let provider: ((event: string, properties: Record<string, unknown>) => void) | null = null;
const queuedEvents: Array<{ event: string; properties: Record<string, unknown> }> = [];

/**
 * Set the analytics provider (e.g. gtag, Segment track). Call from layout or _app.
 * If never set, events are no-ops (or use console in dev).
 */
export function setAnalyticsProvider(
  fn: (event: string, properties: Record<string, unknown>) => void
): void {
  provider = fn;
}

/** Replay events captured before GA/gtag finished loading. */
export function flushQueuedAnalyticsEvents(): void {
  if (!provider) return;
  while (queuedEvents.length > 0) {
    const next = queuedEvents.shift();
    if (next) provider(next.event, next.properties);
  }
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
  } else if (typeof window !== "undefined") {
    queuedEvents.push({ event: eventName, properties: payload });
    if (process.env.NODE_ENV === "development") {
      console.debug("[analytics]", eventName, payload);
    }
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
  /** Vehicle partner page inquiry */
  DRIVER_PARTNER_INQUIRY_SUBMIT: "driver_partner_inquiry_submit",
  /** Zoho SalesIQ */
  ZOHO_CHAT_READY: "zoho_chat_ready",
  ZOHO_CHAT_OPEN: "zoho_chat_open",
  /** Google Business Profile */
  GBP_PROFILE_CLICK: "gbp_profile_click",
  GBP_REVIEW_CLICK: "gbp_review_click",
  /** Core Web Vitals 2.0 RUM (Wave 10) */
  WEB_VITAL: "web_vital",
  WEB_VITAL_BUDGET_EXCEEDED: "web_vital_budget_exceeded",
  /** WhatsApp Business Phase 1 — pre-filled quote follow-up */
  WHATSAPP_QUOTE_CLICK: "whatsapp_quote_click",
  /** WhatsApp mobile live-chat FAB (phone browsers; replaces Zoho) */
  WHATSAPP_CHAT_CLICK: "whatsapp_chat_click",
  /** Welcome capacity guide console */
  CAPACITY_GUIDE_ASK: "capacity_guide_ask",
  CAPACITY_GUIDE_SUGGESTION: "capacity_guide_suggestion",
  CAPACITY_GUIDE_ACTION: "capacity_guide_action",
  CAPACITY_GUIDE_LEAD_CAPTURED: "capacity_guide_lead_captured",
  CAPACITY_GUIDE_APPOINTMENT_BOOKED: "capacity_guide_appointment_booked",
  /** Contact and conversion micro-interactions */
  PHONE_CLICK: "phone_click",
  EMAIL_CLICK: "email_click",
  CASE_STUDY_VIEWED: "case_study_viewed",
  COMPARISON_VIEWED: "comparison_viewed",
  GUIDE_VIEWED: "guide_viewed",
  INDUSTRY_PAGE_VIEW: "industry_page_view",
  LOCATION_PAGE_VIEW: "location_page_view",
  VEHICLE_PAGE_VIEW: "vehicle_page_view",
  INDUSTRY_PAGE_CONVERSION: "industry_page_conversion",
  LOCATION_PAGE_CONVERSION: "location_page_conversion",
  RETURNING_VISITOR: "returning_visitor",
} as const;

/** Mark these as conversions in GA4 Admin → Events → Mark as conversion. */
export const GA4_CONVERSION_EVENTS: readonly string[] = [
  ANALYTICS_EVENTS.CONTACT_FORM_SUBMIT_SUCCESS,
  ANALYTICS_EVENTS.DEMO_REQUEST,
  ANALYTICS_EVENTS.QUOTE_REQUEST,
  ANALYTICS_EVENTS.BUSINESS_INQUIRY_SUBMIT,
  ANALYTICS_EVENTS.DRIVER_PARTNER_INQUIRY_SUBMIT,
  ANALYTICS_EVENTS.BOOKING_QUOTE_SUCCESS,
  ANALYTICS_EVENTS.BOOKING_CONTINUE,
  ANALYTICS_EVENTS.ZOHO_CHAT_OPEN,
  ANALYTICS_EVENTS.WHATSAPP_CHAT_CLICK,
  ANALYTICS_EVENTS.GBP_REVIEW_CLICK,
];
