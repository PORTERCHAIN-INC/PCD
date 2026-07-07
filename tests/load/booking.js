import { check, sleep } from "k6";
import http from "k6/http";
import { Trend } from "k6/metrics";

import { baseUrl, jsonHeaders, quotePayload } from "./lib.js";

const quoteLatency = new Trend("quote_latency", true);

export const options = {
  scenarios: {
    booking: {
      executor: "ramping-vus",
      startVUs: 1,
      stages: [
        { duration: "30s", target: 5 },
        { duration: "1m", target: 10 },
        { duration: "30s", target: 0 },
      ],
      gracefulRampDown: "15s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.02"],
    "http_req_duration{name:health}": ["p(95)<200"],
    "http_req_duration{name:quote}": ["p(95)<3000"],
    quote_latency: ["p(95)<3000"],
  },
};

export default function bookingScenario() {
  const url = baseUrl();
  const health = http.get(`${url}/health`, { tags: { name: "health" } });
  check(health, { "health ok": (r) => r.status === 200 });

  const sessionId = `k6-${__VU}-${__ITER}-${Date.now()}`;
  const quoteRes = http.post(`${url}/v1/quotes`, JSON.stringify(quotePayload(sessionId)), {
    headers: jsonHeaders(),
    tags: { name: "quote" },
  });
  quoteLatency.add(quoteRes.timings.duration);

  const quoteOk = check(quoteRes, {
    "quote created": (r) => r.status === 200,
    "quote has id": (r) => {
      try {
        return Boolean(JSON.parse(r.body).quote_id);
      } catch {
        return false;
      }
    },
  });

  if (quoteOk) {
    const quoteId = JSON.parse(quoteRes.body).quote_id;
    const fetchRes = http.get(`${url}/v1/quotes/${quoteId}`, { tags: { name: "quote_fetch" } });
    check(fetchRes, { "quote fetch ok": (r) => r.status === 200 });
  }

  sleep(0.5);
}
