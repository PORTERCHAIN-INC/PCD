import assert from "node:assert/strict";
import test from "node:test";

import { DimensionUnit, WeightUnit, type Parcel } from "./types.ts";
import {
  calculateVolumetricWeight,
  convertToCm,
  convertToKg,
  serializeParcelsForLegacyAPI,
} from "./units.ts";
import { isOntarioPostal } from "./ontario.ts";
import { parseShopifyOrderToPorterchainRoute } from "./shopifyParser.ts";

test("converts pounds and inches into kilograms and centimetres", () => {
  assert.equal(convertToKg(10, WeightUnit.LBS), 4.536);
  assert.equal(convertToCm(12, DimensionUnit.IN), 30.48);
  assert.equal(convertToCm(1, DimensionUnit.FT), 30.48);
});

test("volumetric weight uses centimetres and divisor 5000", () => {
  assert.equal(calculateVolumetricWeight(10, 10, 10, DimensionUnit.CM), 0.2);
  assert.equal(calculateVolumetricWeight(12, 12, 12, DimensionUnit.IN), 4.424);
});

test("legacy serialization groups identical parcels", () => {
  const parcel = (id: string): Parcel => ({
    id,
    length: 12,
    width: 12,
    height: 12,
    dimensionsUnit: DimensionUnit.IN,
    weight: 5,
    weightUnit: WeightUnit.LBS,
    volumetricWeightKg: 0,
  });
  const other: Parcel = {
    id: "b",
    length: 24,
    width: 12,
    height: 12,
    dimensionsUnit: DimensionUnit.IN,
    weight: 15,
    weightUnit: WeightUnit.LBS,
    volumetricWeightKg: 0,
  };
  const serialized = serializeParcelsForLegacyAPI([parcel("a"), parcel("c"), other]);
  assert.equal(serialized.dimensions, "2x [12x12x12 in, 5 lbs] | 1x [24x12x12 in, 15 lbs]");
  assert.equal(serialized.weight_kg, 11.34);
});

test("ontario postal codes accept GTA FSAs and reject others", () => {
  assert.equal(isOntarioPostal("M5V 2T6"), true);
  assert.equal(isOntarioPostal("k1a0b1"), true);
  assert.equal(isOntarioPostal("V6B 1A1"), false);
  assert.equal(isOntarioPostal("90210"), false);
});

test("shopify parser expands quantity and rejects non-Ontario zips", () => {
  const rejected = parseShopifyOrderToPorterchainRoute({
    shipping_address: {
      address1: "1 Main",
      city: "Vancouver",
      province_code: "BC",
      zip: "V6B 1A1",
    },
    line_items: [{ title: "Box", quantity: 1, grams: 500 }],
  });
  assert.equal(rejected.ok, false);

  const accepted = parseShopifyOrderToPorterchainRoute({
    id: 99,
    name: "#1001",
    shipping_address: {
      address1: "200 Bay St",
      city: "Toronto",
      province_code: "ON",
      zip: "M5J 2J2",
      name: "Receiver",
    },
    line_items: [{ id: 7, title: "Carton", sku: "SKU-1", quantity: 2, grams: 1000 }],
  });
  assert.equal(accepted.ok, true);
  if (accepted.ok) {
    assert.equal(accepted.route.stops[0]?.parcels.length, 2);
    assert.equal(accepted.route.stops[0]?.parcels[0]?.weight, 1);
    assert.equal(accepted.fulfillmentPush.scope, "write_fulfillments");
  }
});
