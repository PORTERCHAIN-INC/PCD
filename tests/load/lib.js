import crypto from "k6/crypto";
import encoding from "k6/encoding";

/** @returns {string} */
export function baseUrl() {
  return (__ENV.API_URL || "http://localhost:8001").replace(/\/$/, "");
}

/** @returns {Record<string, string>} */
export function jsonHeaders() {
  return { "Content-Type": "application/json", Accept: "application/json" };
}

/**
 * Retail quote payload — matches integration tests; uses server-side pricing.
 * @param {string} sessionId
 */
export function quotePayload(sessionId) {
  const scheduled = new Date(Date.now() + 3 * 60 * 60 * 1000).toISOString();
  return {
    anonymous_session_id: sessionId,
    pickup: {
      formatted: "100 King St W, Toronto ON M5X 1A9",
      lat: 43.6488,
      lng: -79.3817,
    },
    dropoff: {
      formatted: "200 Bay St, Toronto ON M5J 2J2",
      lat: 43.6476,
      lng: -79.3797,
    },
    vehicle_class: "cargo_van",
    package_type: "looseParcel",
    weight_kg: 5.0,
    scheduled_at: scheduled,
    schedule_mode: "scheduled",
    website_pricing: {
      customer_price_cad: 48.0,
      driver_payout_cad: 32.0,
      platform_margin_cad: 16.0,
      distance_km: 8.0,
      duration_minutes: 24.0,
      engine_vehicle_id: "cargo_van",
      breakdown: { base: 12.0, distance: 36.0 },
    },
  };
}

/**
 * Decode Stripe webhook signing secret (whsec_ prefix is base64 payload).
 * @param {string} secret
 */
function stripeWebhookKey(secret) {
  if (secret.startsWith("whsec_")) {
    return encoding.b64decode(secret.slice(6), "raw");
  }
  return secret;
}

/**
 * Stripe-compatible webhook signature (HMAC-SHA256).
 * @param {string} payload
 * @param {string} secret
 * @param {number} [timestamp]
 */
export function stripeSignature(payload, secret, timestamp = Math.floor(Date.now() / 1000)) {
  const key = stripeWebhookKey(secret);
  const signedPayload = `${timestamp}.${payload}`;
  const digest = crypto.hmac("sha256", key, signedPayload, "hex");
  return `t=${timestamp},v1=${digest}`;
}

/**
 * Minimal checkout.session.completed event for ingress load tests.
 * @param {string} eventId
 */
export function stripeCheckoutCompletedEvent(eventId) {
  return {
    id: eventId,
    type: "checkout.session.completed",
    data: {
      object: {
        metadata: {},
        payment_intent: "pi_load_test",
        payment_method_types: ["card"],
        amount_total: 4500,
        currency: "cad",
      },
    },
  };
}
