import { check, sleep } from "k6";
import http from "k6/http";
import { Trend } from "k6/metrics";

import { baseUrl, stripeCheckoutCompletedEvent, stripeSignature } from "./lib.js";

const webhookLatency = new Trend("webhook_latency", true);

export const options = {
  scenarios: {
    stripe_webhooks: {
      executor: "constant-arrival-rate",
      rate: 10,
      timeUnit: "1s",
      duration: "1m",
      preAllocatedVUs: 5,
      maxVUs: 20,
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.05"],
    "http_req_duration{name:stripe_webhook}": ["p(95)<1000"],
    webhook_latency: ["p(95)<1000"],
  },
};

export function setup() {
  const secret = (__ENV.STRIPE_WEBHOOK_SECRET || "").trim();
  if (!secret) {
    throw new Error(
      "STRIPE_WEBHOOK_SECRET is required — copy from apps/api/.env or stripe listen --print-secret",
    );
  }

  const probeId = `evt_k6_setup_${Date.now()}`;
  const payload = JSON.stringify(stripeCheckoutCompletedEvent(probeId));
  const probe = http.post(`${baseUrl()}/webhooks/stripe`, payload, {
    headers: {
      "Content-Type": "application/json",
      "stripe-signature": stripeSignature(payload, secret),
    },
    tags: { name: "stripe_webhook_setup" },
  });

  if (probe.status === 503) {
    throw new Error("API returned 503 — set STRIPE_WEBHOOK_SECRET in apps/api/.env and restart the API");
  }
  if (probe.status === 400 && String(probe.body).includes("invalid_signature")) {
    throw new Error(
      "Stripe signature rejected — STRIPE_WEBHOOK_SECRET must match the running API (restart pnpm dev:api after .env changes)",
    );
  }
  if (probe.status !== 200) {
    throw new Error(`Webhook setup probe failed: HTTP ${probe.status} ${probe.body}`);
  }

  return { secret };
}

export default function webhookScenario(data) {
  const url = baseUrl();
  const eventId = `evt_k6_${__VU}_${__ITER}_${Date.now()}`;
  const payload = JSON.stringify(stripeCheckoutCompletedEvent(eventId));
  const signature = stripeSignature(payload, data.secret);

  const res = http.post(`${url}/webhooks/stripe`, payload, {
    headers: {
      "Content-Type": "application/json",
      "stripe-signature": signature,
    },
    tags: { name: "stripe_webhook" },
  });
  webhookLatency.add(res.timings.duration);

  check(res, {
    "webhook accepted": (r) => r.status === 200,
    "webhook status ok": (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.status === "ok" || body.status === "duplicate";
      } catch {
        return false;
      }
    },
  });

  sleep(0.1);
}
