import assert from "node:assert/strict";
import test from "node:test";

import {
  EMPTY_LEAD_FORM,
  assignHeroVariant,
  bucketOf,
  buildLeadPayload,
  normalizeFsa,
  validateLeadForm,
} from "./calculator-lead.ts";

const good = {
  ...EMPTY_LEAD_FORM,
  businessName: "Acme Supply",
  email: "ops@acme.ca",
  phone: "416-555-0100",
  industry: "construction",
  monthlyVolume: "21-100",
};

test("postal codes reduce to an FSA", () => {
  assert.equal(normalizeFsa("m5v 2t6"), "M5V");
  assert.equal(normalizeFsa("L5T"), "L5T");
  assert.equal(normalizeFsa("12345"), "");
  assert.equal(normalizeFsa(undefined), "");
});

test("lead form validation", () => {
  assert.deepEqual(validateLeadForm(good), {});
  const bad = validateLeadForm({ ...EMPTY_LEAD_FORM, email: "x@", phone: "555" });
  assert.deepEqual(Object.keys(bad).sort(), [
    "businessName",
    "email",
    "industry",
    "monthlyVolume",
    "phone",
  ]);
});

test("CASL: marketing consent starts unchecked and is sent separately", () => {
  assert.equal(EMPTY_LEAD_FORM.marketingConsent, false);
  const payload = buildLeadPayload({
    form: good,
    attribution: {
      utm_source: "google",
      utm_campaign: "gta",
      landingPageUrl: "http://localhost:3000/en/delivery",
    },
    estimate: { pickupFsa: "M5V", dropoffFsa: "L5T", vehicle: "cargo_van", amountCents: 12798 },
    visitorId: "vid-1",
    formElapsedMs: 8123.4,
  });
  assert.equal(payload.marketing_consent, false);
  assert.equal(payload.utm_source, "google");
  assert.equal(payload.landing_page, "http://localhost:3000/en/delivery");
  assert.equal(payload.estimate_cents, 12798);
  assert.equal(payload.form_elapsed_ms, 8123);
  assert.equal(payload.website, "");
  const optIn = buildLeadPayload({
    form: { ...good, marketingConsent: true },
    attribution: {},
    formElapsedMs: 5000,
  });
  assert.equal(optIn.marketing_consent, true);
  assert.equal(optIn.pickup_fsa, undefined);
});

test("hero A/B: off by default, deterministic, honours the split", () => {
  assert.equal(assignHeroVariant(null, "v"), "control");
  assert.equal(
    assignHeroVariant({ enabled: false, experiment: "x", split_percent: 100 }, "v"),
    "control"
  );
  assert.equal(
    assignHeroVariant({ enabled: true, experiment: "x", split_percent: 0 }, "v"),
    "control"
  );
  assert.equal(assignHeroVariant({ enabled: true, experiment: "x", split_percent: 100 }, "v"), "b");
  const cfg = { enabled: true, experiment: "hero_copy_v1", split_percent: 50 };
  assert.equal(assignHeroVariant(cfg, "visitor-42"), assignHeroVariant(cfg, "visitor-42"));
  let b = 0;
  for (let i = 0; i < 2000; i += 1) if (assignHeroVariant(cfg, `visitor-${i}`) === "b") b += 1;
  assert.ok(b > 850 && b < 1150, `split ${b}/2000`);
  assert.ok(bucketOf("abc") >= 0 && bucketOf("abc") < 100);
});
