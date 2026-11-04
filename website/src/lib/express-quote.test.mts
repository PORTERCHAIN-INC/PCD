import { test } from "node:test";
import assert from "node:assert/strict";
import { expressQuoteBody, parcelPresetId, parcelSizeFromLink } from "./express-quote";

const trip = {
  pickup: { formatted: "1 Yonge St, Toronto M5E 1W7" },
  dropoff: { formatted: "100 Queen St W, Toronto M5H 2N2" },
  vehicle_class: "sedan_suv",
  scheduled_at: "2026-11-05T15:00:00Z",
};

test("express quote is a parcel quote, never whole-vehicle", () => {
  const body = JSON.parse(expressQuoteBody({ ...trip, parcel_size: "small" as const }));
  assert.equal(body.booking_mode, "parcels");
  assert.deepEqual(body.parcels, [{ preset_id: "small", quantity: 1 }]);
  assert.equal(body.schedule_mode, "now");
  assert.equal("parcel_size" in body, false);
  assert.equal(body.pickup.formatted, trip.pickup.formatted);
});

test("van-size parcel uses the large preset ($9 rate)", () => {
  const body = JSON.parse(expressQuoteBody({ ...trip, parcel_size: "van" as const }));
  assert.deepEqual(body.parcels, [{ preset_id: "large", quantity: 1 }]);
});

test("defaults to small parcel", () => {
  assert.equal(parcelPresetId(undefined), "small");
  assert.deepEqual(JSON.parse(expressQuoteBody({ ...trip, parcel_size: undefined })).parcels, [
    { preset_id: "small", quantity: 1 },
  ]);
});

test("old ?vehicle= links map to a parcel size", () => {
  assert.equal(parcelSizeFromLink("cargo_van"), "van");
  assert.equal(parcelSizeFromLink("box_16"), "van");
  assert.equal(parcelSizeFromLink("sedan_suv"), "small");
  assert.equal(parcelSizeFromLink("van"), "van");
  assert.equal(parcelSizeFromLink(undefined), "small");
});
