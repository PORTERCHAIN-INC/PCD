import assert from "node:assert/strict";
import test from "node:test";

import { parseSignupAttribution } from "./signupAttribution.ts";

test("keeps only attribution keys and trims them", () => {
  const out = parseSignupAttribution(
    "?utm_source=google&utm_campaign=gta-pharmacy&pc_vid=vid-1&token=secret",
    {
      landingPage: "http://localhost:3001/dashboard?utm_source=google",
      referrer: "http://localhost:3000/",
    }
  );
  assert.deepEqual(out, {
    utm_source: "google",
    utm_campaign: "gta-pharmacy",
    pc_vid: "vid-1",
    landing_page: "http://localhost:3001/dashboard?utm_source=google",
    referrer: "http://localhost:3000/",
  });
});

test("no attribution params means nothing is recorded", () => {
  assert.deepEqual(parseSignupAttribution("?tab=orders", { landingPage: "http://x" }), {});
  assert.deepEqual(parseSignupAttribution(""), {});
});
