import type { LogisticsPartner } from "@/lib/dispatch";

export const PARTNER_KIND_LABEL: Record<LogisticsPartner["kind"], string> = {
  courier: "Courier",
  ftl: "Linehaul (FTL)",
  ltl: "Linehaul (LTL)",
  "3pl": "3PL final mile",
  warehouse: "Warehouse",
  cha: "Customs house agent",
};

export const EMPTY_PARTNER: LogisticsPartner = {
  name: "",
  kind: "courier",
  lat: null,
  lng: null,
  fsa_coverage: [],
  rate_per_kg_cents: 0,
  min_charge_cents: 0,
  transit_days: 1,
  cutoff_local: null,
  contact_email: null,
  active: true,
};

/** Client checks that mirror the API (warehouse needs coordinates, name required). */
export function partnerError(p: LogisticsPartner): string | null {
  if (!p.name.trim()) return "Name is required";
  if (p.kind === "warehouse" && (p.lat == null || p.lng == null))
    return "Warehouses need coordinates";
  if (p.contact_email && !p.contact_email.includes("@")) return "Contact email is not valid";
  return null;
}

/** "M5V, L4 k" -> ["M5V", "L4", "K"] */
export function parseCoverage(raw: string): string[] {
  return raw
    .replace(/,/g, " ")
    .split(/\s+/)
    .filter(Boolean)
    .map((c) => c.toUpperCase().slice(0, 3));
}
