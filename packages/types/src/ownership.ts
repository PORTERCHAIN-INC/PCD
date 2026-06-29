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
