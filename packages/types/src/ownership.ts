export type DataOwnership = "porterchain" | "fleetbase";

export const PORTERCHAIN_OWNED = [
  "users",
  "merchants",
  "visitors",
  "quotes",
  "contracts",
  "pricing",
  "invoices",
  "billing",
  "crm",
  "notifications",
  "analytics",
  "reports",
] as const;

/**
 * Fleetbase owns dispatch fleet assets (live GPS, POD, console vehicles).
 * PorterChain `vehicles` table is a commercial/admin *mirror* — class ids
 * must be Capacity Catalog snake ids (`vehicle_types` / customer_goods).
 * Capacity catalog, quotes (booked class), and preferred_vehicles are PC-owned.
 */
export const FLEETBASE_OWNED = [
  "vehicles",
  "drivers",
  "orders",
  "dispatch",
  "routes",
  "gps",
  "waypoints",
  "tracking",
  "proof_of_delivery",
] as const;
