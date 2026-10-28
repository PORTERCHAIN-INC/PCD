/** Shared merchant order wire fields (keep in sync with MerchantOrderResponse). */

export type MerchantOrder = {
  order_id: string;
  order_number: string;
  tracking_number: string;
  state: string;
  amount_cents: number;
  currency: string;
  scheduled_at: string;
  pickup: Record<string, unknown>;
  dropoff: Record<string, unknown>;
  internal_reference?: string | null;
  purchase_order_number?: string | null;
  cost_centre?: string | null;
  /** True when the booking is sandbox/test capacity (no live dispatch). */
  is_sandbox: boolean;
  created_at: string;
};

/** Per-box chain-of-custody status (packages.status; keep in sync with domain/states.PackageState). */
export const PACKAGE_CUSTODY_STATES = [
  "manifested",
  "picked_up",
  "loaded",
  "out_for_delivery",
  "delivered",
  "missing_at_pickup",
] as const;
export type PackageCustodyState = (typeof PACKAGE_CUSTODY_STATES)[number];

/** Where a partner barcode on a box came from (external_identifier_service.SOURCES). */
export const EXTERNAL_ID_SOURCES = [
  "merchant",
  "shopify",
  "marketplace",
  "partner_carrier",
] as const;
export type ExternalIdSource = (typeof EXTERNAL_ID_SOURCES)[number];

/** GET /v1/merchant/orders/{id}/external-ids */
export type PackageExternalIdsResponse = {
  items: Array<{
    id: string;
    package_id: string;
    source: ExternalIdSource;
    value: string;
    created_at: string | null;
  }>;
  packages: Array<{
    id: string;
    parcel_index: number;
    total_parcels: number;
    tracking_suffix: string;
    status: PackageCustodyState;
  }>;
};
