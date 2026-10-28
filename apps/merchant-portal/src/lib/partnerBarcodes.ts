import type { ExternalIdSource, PackageExternalIdsResponse } from "@porterchain/types";

export const SOURCE_LABEL: Record<ExternalIdSource, string> = {
  merchant: "Your barcode",
  shopify: "Shopify",
  marketplace: "Marketplace",
  partner_carrier: "Partner carrier",
};

const STATUS_LABEL: Record<string, string> = {
  manifested: "Waiting for pickup",
  picked_up: "Picked up",
  loaded: "Loaded",
  out_for_delivery: "Out for delivery",
  delivered: "Delivered",
  missing_at_pickup: "Missing at pickup",
};

export function custodyStatusLabel(status: string): string {
  return STATUS_LABEL[status] ?? status.replace(/_/g, " ");
}

/** The barcodes registered for one box. */
export function barcodesFor(
  data: PackageExternalIdsResponse,
  packageId: string
): PackageExternalIdsResponse["items"] {
  return data.items.filter((i) => i.package_id === packageId);
}
