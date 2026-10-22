import assert from "node:assert/strict";
import test from "node:test";

import { billingSummaryLine, termsLabel } from "./billingLine.ts";
import { postalFromAddress, normalizePostal } from "./ontario.ts";
import { validateRouteJob } from "./toRouteImport.ts";
import type { RouteJob } from "./types.ts";

// Reproduces the planner crash: an incomplete billing overview ({}) used to reach
// `terms.replace(...)` and threw "Cannot read properties of undefined (reading 'replace')".
test("old terms formatter crashed on an incomplete billing overview", () => {
  const legacyFormatTerms = (terms: string) => terms.replace(/_/g, " ");
  const incomplete = {} as { payment_terms: string };
  assert.throws(() => legacyFormatTerms(incomplete.payment_terms), /reading 'replace'/);
});

test("billing line tolerates an incomplete overview", () => {
  assert.equal(billingSummaryLine({}), null);
  assert.equal(billingSummaryLine(null), null);
  assert.equal(billingSummaryLine(undefined), null);
  assert.equal(billingSummaryLine({ billing_cycle: "MONTHLY" }), "Payment terms not set · Monthly");
  assert.equal(
    billingSummaryLine({
      payment_terms: "net_30",
      billing_cycle: "WEEKLY",
      contract_pricing: { has_contract: true, contract_name: "Acme" },
    }),
    "Net 30 · Weekly · Acme"
  );
  assert.equal(termsLabel(undefined), "Payment terms not set");
});

test("postal helpers tolerate missing values", () => {
  assert.equal(normalizePostal(undefined), "");
  assert.equal(postalFromAddress(undefined, undefined), "");
});

test("validateRouteJob never throws on missing stop fields", () => {
  const broken = {
    pickupLocation: {},
    stops: [{}, { formattedAddress: "1 King St W, Toronto ON M5H 1A1", parcels: [{}] }, null],
  } as unknown as RouteJob;
  const result = validateRouteJob(broken);
  assert.equal(result.ok, false);
  assert.ok(result.errors.includes("Pickup address is required"));
  assert.ok(result.errors.includes("Stop 1: address is required"));
  assert.ok(result.errors.includes("Stop 1: customer name is required"));
  assert.ok(result.errors.includes("Stop 1: add at least one parcel"));
  assert.ok(result.errors.includes("Stop 2 parcel 1: weight must be greater than 0"));
  assert.ok(result.errors.includes("Stop 3: address is required"));
  assert.ok(
    result.warnings.includes(
      "Stop 2: no map pin yet. Pick the address from the suggestions to be exact"
    )
  );
  assert.deepEqual(validateRouteJob(undefined).errors, [
    "Pickup address is required",
    "Add at least one delivery stop",
  ]);
});

test("validateRouteJob flags invalid coordinates as errors", () => {
  const job = {
    pickupLocation: {
      formattedAddress: "100 Queen St W, Toronto ON M5H 2N2",
      latitude: Number.NaN,
      longitude: -79.38,
    },
    stops: [
      {
        formattedAddress: "1 King St W, Toronto ON M5H 1A1",
        customerName: "Ana",
        postalCode: "M5H 1A1",
        latitude: 0,
        longitude: 0,
        parcels: [{ weight: 1, length: 1, width: 1, height: 1 }],
      },
    ],
  } as unknown as RouteJob;
  const result = validateRouteJob(job);
  assert.deepEqual(result.errors, [
    "Pickup: the map location is invalid. Pick the address again from the suggestions",
    "Stop 1: the map location is invalid. Pick the address again from the suggestions",
  ]);
});
