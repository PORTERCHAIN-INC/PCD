/**
 * Shopify orders/create and fulfillment_orders/placed → PorterChain route draft.
 *
 * Access scopes this ingest depends on:
 * - read_orders — order, shipping_address, line_items, customer
 * - read_assigned_fulfillment_orders — fulfillment order destination when present
 *
 * After confirm, PorterChain can push live tracking with write_fulfillments
 * (tracking URL + ETA). This parser does not call Shopify.
 */

import { isOntarioPostal, isOntarioProvince } from "./ontario.ts";
import {
  DimensionUnit,
  RouteJobStatus,
  WeightUnit,
  type Parcel,
  type RouteStop,
  type ShopifyParseResult,
} from "./types.ts";
import { withVolumetricWeight } from "./units.ts";

const TRACKING_BASE = "https://porterchain.com/track";

interface ShopifyAddress {
  address1?: string;
  address2?: string;
  city?: string;
  province?: string;
  province_code?: string;
  zip?: string;
  country?: string;
  country_code?: string;
  name?: string;
  phone?: string;
  latitude?: number;
  longitude?: number;
}

interface ShopifyLineItemProperty {
  name?: string;
  value?: string;
}

interface ShopifyLineItem {
  id?: number | string;
  title?: string;
  name?: string;
  sku?: string;
  quantity?: number;
  grams?: number;
  weight?: number;
  properties?: ShopifyLineItemProperty[];
}

interface ShopifyOrderPayload {
  id?: number | string;
  name?: string;
  email?: string;
  phone?: string;
  shipping_address?: ShopifyAddress;
  destination?: ShopifyAddress;
  customer?: { email?: string; phone?: string; first_name?: string; last_name?: string };
  line_items?: ShopifyLineItem[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asString(value: unknown): string | undefined {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return undefined;
}

function asNumber(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() && Number.isFinite(Number(value)))
    return Number(value);
  return undefined;
}

function readAddress(record: Record<string, unknown>): ShopifyAddress | undefined {
  const raw = record.shipping_address ?? record.destination;
  if (!isRecord(raw)) return undefined;
  return {
    address1: asString(raw.address1),
    address2: asString(raw.address2),
    city: asString(raw.city),
    province: asString(raw.province),
    province_code: asString(raw.province_code),
    zip: asString(raw.zip),
    country: asString(raw.country),
    country_code: asString(raw.country_code),
    name: asString(raw.name),
    phone: asString(raw.phone),
    latitude: asNumber(raw.latitude),
    longitude: asNumber(raw.longitude),
  };
}

function formatAddress(address: ShopifyAddress): string {
  return [
    address.address1,
    address.address2,
    address.city,
    address.province_code ?? address.province,
    address.zip,
    "Canada",
  ]
    .filter(Boolean)
    .join(", ");
}

function propertyMap(item: ShopifyLineItem): Map<string, string> {
  const map = new Map<string, string>();
  for (const prop of item.properties ?? []) {
    const name = prop.name?.trim().toLowerCase();
    const value = prop.value?.trim();
    if (name && value) map.set(name, value);
  }
  return map;
}

function readDimension(
  props: Map<string, string>,
  keys: string[]
): { value: number; unit: DimensionUnit } | undefined {
  for (const key of keys) {
    const raw = props.get(key);
    if (!raw) continue;
    const match = raw.match(/^(-?\d+(?:\.\d+)?)\s*(in|ft|cm)?$/i);
    if (!match) continue;
    const value = Number(match[1]);
    if (!Number.isFinite(value) || value <= 0) continue;
    const unitToken = (match[2] ?? DimensionUnit.CM).toLowerCase();
    const unit =
      unitToken === "in"
        ? DimensionUnit.IN
        : unitToken === "ft"
          ? DimensionUnit.FT
          : DimensionUnit.CM;
    return { value, unit };
  }
  return undefined;
}

function parcelsFromLineItem(item: ShopifyLineItem, index: number): Parcel[] {
  const quantity = Math.max(1, Math.floor(item.quantity ?? 1));
  const title = item.title || item.name || `Item ${index + 1}`;
  const props = propertyMap(item);
  const length = readDimension(props, ["length", "l"]);
  const width = readDimension(props, ["width", "w"]);
  const height = readDimension(props, ["height", "h"]);
  const unit = length?.unit ?? width?.unit ?? height?.unit ?? DimensionUnit.CM;
  const grams = item.grams ?? (item.weight != null && item.weight > 0 ? item.weight : undefined);
  const weightKg = grams != null && grams > 0 ? grams / 1000 : 0;

  const parcels: Parcel[] = [];
  for (let copy = 0; copy < quantity; copy += 1) {
    parcels.push(
      withVolumetricWeight({
        id: `shopify-${item.id ?? index}-${copy + 1}`,
        sku: item.sku,
        name: title,
        length: length?.value ?? 0,
        width: width?.value ?? 0,
        height: height?.value ?? 0,
        dimensionsUnit: unit,
        weight: weightKg,
        weightUnit: WeightUnit.KG,
      })
    );
  }
  return parcels;
}

function newRouteId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `route-${Date.now()}`;
}

export function parseShopifyOrderToPorterchainRoute(shopifyPayload: unknown): ShopifyParseResult {
  if (!isRecord(shopifyPayload)) {
    return { ok: false, errors: ["Shopify payload must be an object"] };
  }

  const payload = shopifyPayload as ShopifyOrderPayload;
  const address = readAddress(shopifyPayload);
  if (!address) {
    return { ok: false, errors: ["Missing shipping_address"] };
  }

  const errors: string[] = [];
  const province = address.province_code ?? address.province;
  if (!isOntarioProvince(province)) {
    errors.push("Shipping address is outside Ontario");
  }
  if (!isOntarioPostal(address.zip)) {
    errors.push("Postal code must be an Ontario code (FSA K, L, M, N, or P)");
  }
  if (!address.address1) {
    errors.push("Shipping address line is missing");
  }
  if (errors.length > 0) return { ok: false, errors };

  const lineItems = Array.isArray(shopifyPayload.line_items)
    ? shopifyPayload.line_items.filter(isRecord)
    : [];
  const parcels = lineItems.flatMap((item, index) =>
    parcelsFromLineItem(
      {
        id: asString(item.id) ?? asNumber(item.id),
        title: asString(item.title),
        name: asString(item.name),
        sku: asString(item.sku),
        quantity: asNumber(item.quantity),
        grams: asNumber(item.grams),
        weight: asNumber(item.weight),
        properties: Array.isArray(item.properties)
          ? item.properties.filter(isRecord).map((prop) => ({
              name: asString(prop.name),
              value: asString(prop.value),
            }))
          : undefined,
      },
      index
    )
  );
  if (parcels.length === 0) {
    errors.push("Order has no line items to convert into parcels");
    return { ok: false, errors };
  }

  const customer = isRecord(shopifyPayload.customer) ? shopifyPayload.customer : undefined;
  const customerName =
    address.name ||
    [asString(customer?.first_name), asString(customer?.last_name)].filter(Boolean).join(" ") ||
    "Shopify customer";

  const stop: RouteStop = {
    id: `shopify-stop-${asString(payload.id) ?? "1"}`,
    stopSequence: 1,
    formattedAddress: formatAddress(address),
    latitude: address.latitude,
    longitude: address.longitude,
    postalCode: address.zip ?? "",
    customerName,
    customerPhone: address.phone || asString(customer?.phone) || asString(payload.phone),
    customerEmail: asString(payload.email) || asString(customer?.email),
    parcels,
  };

  const orderId = asString(payload.id) ?? "";
  return {
    ok: true,
    shopifyOrderId: orderId,
    shopifyOrderName: asString(payload.name),
    route: {
      routeId: newRouteId(),
      pickupLocation: { formattedAddress: "" },
      stops: [stop],
      totalRouteWeightKg: 0,
      status: RouteJobStatus.DRAFT,
      internalReference: asString(payload.name) ?? (orderId ? `shopify-${orderId}` : undefined),
    },
    fulfillmentPush: {
      scope: "write_fulfillments",
      tracking_company: "PorterChain",
      tracking_url: orderId
        ? `${TRACKING_BASE}?shopify_order=${encodeURIComponent(orderId)}`
        : TRACKING_BASE,
      notify_customer: true,
    },
  };
}
