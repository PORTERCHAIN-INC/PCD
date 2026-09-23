/** FSA (postal-code) flat rates — `/v1/pricing/components/fsa`. */

import { adminFetch } from "@/lib/api";

const B = "/v1/pricing/components/fsa";

export type FsaRate = {
  id: string;
  dest_fsa: string;
  flat_cents: number;
  /** null means the rate applies to every merchant. */
  merchant_id: string | null;
  /** null means the rate applies regardless of where the trip starts. */
  origin_fsa: string | null;
  /** null means the rate applies to every vehicle class. */
  vehicle_class: string | null;
  /** When true the flat price already covers the downtown / upper-zone fees. */
  includes_location_fees: boolean;
  label: string | null;
  is_active: boolean;
  /** e.g. `{ tier: "T1" }` for schedule route minimums. */
  config?: Record<string, unknown> | null;
};

export type FsaRateInput = Omit<FsaRate, "id">;

export type FsaQuoteResult = {
  component: string;
  total_cents: number;
  items: Array<{ code: string; label: string; amount_cents: number }>;
  metadata: {
    origin_fsa: string;
    dest_fsa: string;
    matched: boolean;
    reason?: string;
    rate_id?: string;
    includes_location_fees?: boolean;
    merchant_scoped?: boolean;
  };
};

export type FsaCoverageGap = {
  tile_fsa_count: number;
  rated_in_tile_count: number;
  missing_rate_count: number;
  extra_out_of_tile_count: number;
  missing_sample: string[];
  extra_sample: string[];
  scope: string;
  merchant_id?: string | null;
  note?: string;
};

export type FsaBulkResult = {
  created: number;
  updated: number;
  error_count: number;
  errors: Array<{ index: string; dest_fsa: string; error: string }>;
  note?: string;
};

export const fsaRates = {
  list: (token: string, merchantId?: string) =>
    adminFetch<FsaRate[]>(
      `${B}/rates${merchantId ? `?merchant_id=${encodeURIComponent(merchantId)}` : ""}`,
      token
    ),
  create: (token: string, body: FsaRateInput) =>
    adminFetch<FsaRate>(`${B}/rates`, token, { method: "POST", body: JSON.stringify(body) }),
  update: (token: string, id: string, body: FsaRateInput) =>
    adminFetch<FsaRate>(`${B}/rates/${id}`, token, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  remove: (token: string, id: string) =>
    adminFetch<void>(`${B}/rates/${id}`, token, { method: "DELETE" }),
  coverageGap: (token: string, merchantId?: string) =>
    adminFetch<FsaCoverageGap>(
      `${B}/coverage-gap${merchantId ? `?merchant_id=${encodeURIComponent(merchantId)}` : ""}`,
      token
    ),
  bulk: (token: string, rates: FsaRateInput[], merchantId?: string | null) =>
    adminFetch<FsaBulkResult>(`${B}/rates/bulk`, token, {
      method: "POST",
      body: JSON.stringify({ rates, merchant_id: merchantId ?? null }),
    }),
  /** Dry-run a lookup to see which rate a given trip would match. */
  quote: (
    token: string,
    body: { dest_fsa: string; origin_fsa?: string; merchant_id?: string; vehicle_class?: string }
  ) => adminFetch<FsaQuoteResult>(B, token, { method: "POST", body: JSON.stringify(body) }),
};

/** Uppercase three-character FSA, or empty when the input has none. */
export function normalizeFsa(value: string): string {
  const candidate = value.trim().toUpperCase().replace(/\s/g, "");
  return /^[A-Z]\d[A-Z]/.test(candidate) ? candidate.slice(0, 3) : "";
}
