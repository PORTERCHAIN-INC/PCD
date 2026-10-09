import assert from "node:assert/strict";
import test from "node:test";

import {
  cleanInstructions,
  etaWindowText,
  isEnhancedExperience,
  manageErrorText,
  safeBrandColor,
  statusHeadline,
  stopsAwayText,
} from "../src/trackingExperience.ts";

const base = {
  enhanced: true,
  tracking_number: "PC1",
  state: "IN_TRANSIT",
  branding: {},
  progress: [],
  timeline: [],
  eta_window: null,
  stops_away: null,
  driver: null,
  proof_of_delivery: null,
  attempts: 0,
  awaiting_schedule: false,
  returning_to_sender: false,
  help: { email: null, phone: null, url: null },
  self_service: { available: false },
  rules: { id_required: false, signature_required: false, safe_place_allowed: true },
};

test("brand colour only accepts strict hex", () => {
  assert.equal(safeBrandColor("#AABBCC"), "#aabbcc");
  assert.equal(safeBrandColor("red"), "#1e3a5f");
  assert.equal(safeBrandColor("#abc; background:url(x)", "#000000"), "#000000");
  assert.equal(safeBrandColor(null), "#1e3a5f");
});

test("enhanced flag gates the branded page", () => {
  assert.equal(isEnhancedExperience({ enhanced: false, tracking_number: "x" }), false);
  assert.equal(isEnhancedExperience(null), false);
  assert.equal(isEnhancedExperience(base), true);
});

test("stops away copy", () => {
  assert.equal(stopsAwayText(null), null);
  assert.equal(stopsAwayText(0), "You're next");
  assert.equal(stopsAwayText(1), "1 stop before yours");
  assert.equal(stopsAwayText(3), "3 stops before yours");
  assert.equal(stopsAwayText(0, "AT_DESTINATION"), "Your driver has arrived");
});

test("eta window text prefers label, then formats in Toronto time", () => {
  assert.equal(etaWindowText(null), null);
  assert.equal(
    etaWindowText({ start: null, end: null, label: "Fri Oct 9, 2pm-9pm", source: "promise" }),
    "Fri Oct 9, 2pm-9pm"
  );
  const text = etaWindowText({
    start: "2026-10-09T18:00:00Z",
    end: "2026-10-10T01:00:00Z",
    label: null,
    source: "customer",
  });
  assert.match(text ?? "", /Oct 9/);
  assert.match(text ?? "", /2pm-9pm/);
  assert.match(
    etaWindowText({ start: "2026-10-09T18:00:00Z", end: null, label: null, source: "booking" }) ??
      "",
    /from 2pm/
  );
});

test("status headline", () => {
  assert.equal(statusHeadline({ ...base, stops_away: 0 }), "You're next");
  assert.equal(statusHeadline(base), "Out for delivery");
  assert.equal(statusHeadline({ ...base, state: "POD_COMPLETED" }), "Delivered");
  assert.equal(statusHeadline({ ...base, state: "FAILED" }), "Delivery attempted");
  assert.equal(statusHeadline({ ...base, returning_to_sender: true }), "Returning to sender");
  assert.equal(
    statusHeadline({ ...base, state: "BOOKED", awaiting_schedule: true }),
    "Choose a delivery time"
  );
});

test("manage errors and instruction cleaning", () => {
  assert.match(manageErrorText("link_expired"), /expired/);
  assert.match(manageErrorText("nope"), /Something went wrong/);
  assert.deepEqual(
    cleanInstructions(
      { gate_code: " 12 ", buzzer: "", safe_place: "porch", notes: "  " },
      { safe_place_allowed: false }
    ),
    { gate_code: "12" }
  );
  assert.deepEqual(cleanInstructions({ safe_place: "porch" }, { safe_place_allowed: true }), {
    safe_place: "porch",
  });
});
