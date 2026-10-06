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
  "leads",
  "abandoned_checkouts",
  "domain_events",
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

/** Empty. Dispatch, GPS, and proof belong to PorterChain. */
export const FLEETBASE_OWNED = [] as const;
