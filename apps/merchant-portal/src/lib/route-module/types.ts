/**
 * Merchant route planner domain.
 * Replaces the flat "one weight / one dimensions string per job" stop model
 * with parcels nested under each stop. Legacy booking fields are derived
 * in units.ts — they are not the source of truth.
 */

export const DimensionUnit = {
  IN: "in",
  FT: "ft",
  CM: "cm",
} as const;

export type DimensionUnit = (typeof DimensionUnit)[keyof typeof DimensionUnit];

export const WeightUnit = {
  LBS: "lbs",
  KG: "kg",
} as const;

export type WeightUnit = (typeof WeightUnit)[keyof typeof WeightUnit];

/** Catalog ids accepted by POST /v1/merchant/route-imports. */
export const MerchantVehicleClass = {
  SEDAN: "sedan",
  SUV: "suv",
  PICKUP: "pickup",
  CARGO_VAN: "cargoVan",
  HIGH_ROOF: "highRoof",
  BOX_16: "box16",
  BOX_20: "box20",
} as const;

export type MerchantVehicleClass = (typeof MerchantVehicleClass)[keyof typeof MerchantVehicleClass];

/** Banner label shown to the merchant. Not sent to the booking API. */
export const FleetBand = {
  SEDAN: "sedan",
  CARGO_VAN: "cargo_van",
  BOX_TRUCK: "box_truck",
  OVER_CAPACITY: "over_capacity",
} as const;

export type FleetBand = (typeof FleetBand)[keyof typeof FleetBand];

export const RouteJobStatus = {
  DRAFT: "draft",
  QUOTED: "quoted",
  CONFIRMED: "confirmed",
} as const;

export type RouteJobStatus = (typeof RouteJobStatus)[keyof typeof RouteJobStatus];

export interface Parcel {
  id: string;
  sku?: string;
  /** Display name; defaults to sku or "Parcel". */
  name?: string;
  length: number;
  width: number;
  height: number;
  dimensionsUnit: DimensionUnit;
  weight: number;
  weightUnit: WeightUnit;
  /** kg, cm³ / 5000 after unit conversion. */
  volumetricWeightKg: number;
}

export interface PickupLocation {
  formattedAddress: string;
  latitude?: number;
  longitude?: number;
  postalCode?: string;
  unit?: string;
  contactName?: string;
  contactPhone?: string;
}

export interface RouteStop {
  id: string;
  stopSequence: number;
  formattedAddress: string;
  latitude?: number;
  longitude?: number;
  postalCode: string;
  customerName: string;
  customerPhone?: string;
  customerEmail?: string;
  deliveryNotes?: string;
  parcels: Parcel[];
}

export interface RouteJob {
  routeId: string;
  merchantId?: string;
  pickupLocation: PickupLocation;
  stops: RouteStop[];
  assignedVehicleClass: MerchantVehicleClass;
  totalRouteWeightKg: number;
  status: RouteJobStatus;
  scheduledAt?: string;
  internalReference?: string;
  constructionSite?: boolean;
  siteAccessNotes?: string;
  requiresLiftgate?: boolean;
}

export interface LegacyParcelSerialization {
  weight_kg: number;
  dimensions: string;
}

export interface RouteImportPackagePayload {
  id: string;
  name: string;
  sku?: string;
  quantity: number;
  weight_kg: number;
  length_cm: number;
  width_cm: number;
  height_cm: number;
  dimensions: string;
}

export interface RouteImportStopPayload {
  sequence: number;
  stop_type: "pickup" | "drop";
  address: string;
  unit?: string;
  postal?: string;
  lat?: number;
  lng?: number;
  contact_name?: string;
  contact_phone?: string;
  contact_email?: string;
  notes?: string;
  packages?: RouteImportPackagePayload[];
}

export interface RouteImportCreatePayload {
  schema_version: "route_import.v1";
  source: "portal";
  vehicle_class: MerchantVehicleClass;
  scheduled_at?: string;
  package_type: "looseParcel";
  internal_reference?: string;
  weight_kg: number;
  dimensions: string;
  requires_liftgate?: boolean;
  site_access_notes?: string;
  stops: RouteImportStopPayload[];
}

export interface ShopifyFulfillmentPush {
  /** Relies on Shopify access scope write_fulfillments. */
  scope: "write_fulfillments";
  tracking_company: "PorterChain";
  tracking_url: string;
  tracking_number?: string;
  notify_customer: boolean;
}

export interface ShopifyParseSuccess {
  ok: true;
  shopifyOrderId: string;
  shopifyOrderName?: string;
  route: Omit<RouteJob, "merchantId" | "status" | "assignedVehicleClass" | "totalRouteWeightKg"> & {
    assignedVehicleClass?: MerchantVehicleClass;
    totalRouteWeightKg: number;
    status: RouteJobStatus;
  };
  /**
   * Shape PorterChain can POST back after confirm.
   * Ingest uses read_orders and read_assigned_fulfillment_orders.
   * This slice does not call Shopify.
   */
  fulfillmentPush: ShopifyFulfillmentPush;
}

export interface ShopifyParseFailure {
  ok: false;
  errors: string[];
}

export type ShopifyParseResult = ShopifyParseSuccess | ShopifyParseFailure;
