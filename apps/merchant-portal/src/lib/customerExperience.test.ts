import assert from "node:assert/strict";
import test from "node:test";

import {
  contrastOnWhite,
  cxCustomerFacingSummary,
  cxValidationError,
  type CustomerExperienceSettings,
} from "./customerExperience.ts";

const defaults: CustomerExperienceSettings = {
  tracking: {
    branded_page: false,
    show_driver_first_name: true,
    show_stops_away: true,
    show_pod_photo: false,
    support_email: null,
    support_phone: null,
    help_url: null,
  },
  notifications: {
    enabled: false,
    channels: { email: true, sms: false, whatsapp: false },
    events: {
      out_for_delivery: true,
      next_stop: true,
      eta_20: true,
      delivered: true,
      attempted: true,
      schedule_request: true,
      rescheduled: true,
    },
    next_stop_threshold: 1,
    eta_minutes: 20,
    language: "auto",
    eta_min_interval_minutes: 15,
    quiet_hours: { enabled: true, start: "21:00", end: "08:00", timezone: "America/Toronto" },
  },
  self_service: {
    enabled: false,
    link_ttl_hours: 72,
    allow_reschedule: true,
    allow_instructions: true,
    schedule_days: 7,
  },
  delivery_rules: {
    safe_place_allowed: true,
    id_required: false,
    signature_required: false,
    require_schedule_for_bulky: false,
    bulky_package_types: ["furniture"],
    bulky_vehicle_classes: [],
  },
  reattempt: { enabled: false, max_attempts: 2, return_to_sender_after: 2 },
};

test("defaults change nothing customers see", () => {
  assert.deepEqual(cxCustomerFacingSummary(defaults), []);
  assert.equal(cxValidationError(defaults), null);
});

test("summary lists what recipients will get", () => {
  const on: CustomerExperienceSettings = {
    ...defaults,
    tracking: { ...defaults.tracking, branded_page: true },
    notifications: {
      ...defaults.notifications,
      enabled: true,
      channels: { email: true, sms: true, whatsapp: false },
    },
    self_service: { ...defaults.self_service, enabled: true },
    delivery_rules: { ...defaults.delivery_rules, require_schedule_for_bulky: true },
    reattempt: { enabled: true, max_attempts: 2, return_to_sender_after: 3 },
  };
  const lines = cxCustomerFacingSummary(on);
  assert.equal(lines.length, 5);
  assert.match(lines[1] ?? "", /7 delivery update\(s\) by email \+ sms/);
  assert.match(lines[4] ?? "", /return to sender after 3/);
});

test("validation mirrors the API", () => {
  const bad = (patch: Partial<CustomerExperienceSettings>) =>
    cxValidationError({ ...defaults, ...patch });
  assert.match(
    bad({
      notifications: {
        ...defaults.notifications,
        quiet_hours: { ...defaults.notifications.quiet_hours, start: "9pm" },
      },
    }) ?? "",
    /Quiet hours/
  );
  assert.match(bad({ tracking: { ...defaults.tracking, help_url: "http://x" } }) ?? "", /https/);
  assert.match(bad({ tracking: { ...defaults.tracking, support_email: "nope" } }) ?? "", /email/);
  assert.match(
    bad({ notifications: { ...defaults.notifications, eta_minutes: 2 } }) ?? "",
    /5 and 120/
  );
});

test("email branding: AA check and validation", () => {
  assert.ok(contrastOnWhite("#0b1220") > 15);
  assert.ok(contrastOnWhite("#0f766e") >= 4.5);
  assert.ok(contrastOnWhite("#fde047") < 4.5);
  assert.equal(contrastOnWhite("teal"), 0);
  const base = structuredClone(defaults);
  base.notifications.reply_to = "not-an-email";
  assert.match(cxValidationError(base) ?? "", /reply-to/);
  base.notifications.reply_to = "help@shop.ca";
  base.notifications.logo_url = "http://x.test/l.png";
  assert.match(cxValidationError(base) ?? "", /https/);
  base.notifications.logo_url = "https://x.test/l.png";
  base.notifications.brand_color = "#0f766e";
  assert.equal(cxValidationError(base), null);
});
