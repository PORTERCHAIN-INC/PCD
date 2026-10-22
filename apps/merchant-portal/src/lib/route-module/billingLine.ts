/**
 * The terms line above the route planner. The billing overview can come back incomplete
 * (new merchant, API hiccup, older API): every field is optional here so the planner never
 * crashes on it ("Cannot read properties of undefined (reading 'replace')").
 */
export type BillingLineInput = {
  payment_terms?: string | null;
  billing_cycle?: string | null;
  net_terms_days?: number | null;
  contract_pricing?: { has_contract?: boolean | null; contract_name?: string | null } | null;
} | null;

export function termsLabel(terms: string | null | undefined): string {
  const t = typeof terms === "string" ? terms.trim() : "";
  if (!t) return "Payment terms not set";
  return t.replace(/_/g, " ").replace(/\bnet\b/i, "Net");
}

export function cycleLabel(cycle: string | null | undefined): string {
  const c = typeof cycle === "string" ? cycle.trim() : "";
  if (!c) return "billing cycle not set";
  return c.charAt(0).toUpperCase() + c.slice(1).toLowerCase();
}

/** "Net 30 · Monthly · Acme contract", or null when there is nothing to show. */
export function billingSummaryLine(billing: BillingLineInput | undefined): string | null {
  if (!billing || typeof billing !== "object") return null;
  if (!billing.payment_terms && !billing.billing_cycle && !billing.contract_pricing) return null;
  const parts = [termsLabel(billing.payment_terms)];
  if (billing.net_terms_days) parts[0] += ` · Net ${billing.net_terms_days}`;
  parts.push(cycleLabel(billing.billing_cycle));
  const contract = billing.contract_pricing;
  if (contract?.has_contract && contract.contract_name) parts.push(contract.contract_name);
  return parts.join(" · ");
}
