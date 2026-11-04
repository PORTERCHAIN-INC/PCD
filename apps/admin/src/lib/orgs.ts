import { adminFetch } from "@/lib/api";

/** Doc 70: organisations, business types, capability packs and operating profiles. */
export type Org = {
  id: string;
  public_id: string;
  display_name: string;
  legal_name: string | null;
  business_type: string;
  subtype: string | null;
  role_flags: string[];
  status: string;
  locale: string | null;
  merchant_id: string | null;
  needs_review: boolean;
  capabilities: Record<string, boolean>;
  profile: { version: number; [k: string]: unknown } | null;
  documents: string[];
};

export type OrgList = {
  items: Org[];
  total?: number;
  counts?: { by_type: Record<string, number>; needs_review: number; all: number };
};

export type BusinessType = {
  code: string;
  label: string;
  label_en?: string;
  label_fr?: string;
  roles: string[];
  subtypes?: string[];
  documents: string[];
};
export type BusinessTypes = {
  business_types: BusinessType[];
  capabilities: Record<string, string>;
  subtype_capabilities: Record<string, string[]>;
};

const json = (method: string, body: unknown) => ({ method, body: JSON.stringify(body) });

export const orgsApi = {
  types: async (t: string) => {
    const r = await adminFetch<BusinessTypes>("/v1/admin/orgs/business-types", t);
    // API sends label_en / label_fr; admin is EN-only, so normalise to `label`.
    r.business_types = r.business_types.map((b) => ({
      ...b,
      label: b.label ?? b.label_en ?? b.code.replace(/_/g, " "),
    }));
    return r;
  },
  list: (
    t: string,
    q: {
      business_type?: string;
      needs_review?: boolean;
      status?: string;
      q?: string;
      limit?: number;
      offset?: number;
    } = {}
  ) => {
    const p = new URLSearchParams();
    if (q.business_type) p.set("business_type", q.business_type);
    if (q.needs_review != null) p.set("needs_review", String(q.needs_review));
    if (q.status) p.set("status", q.status);
    if (q.q?.trim()) p.set("q", q.q.trim());
    if (q.limit) p.set("limit", String(q.limit));
    if (q.offset) p.set("offset", String(q.offset));
    return adminFetch<OrgList>(`/v1/admin/orgs?${p}`, t);
  },
  get: (t: string, id: string) => adminFetch<Org>(`/v1/admin/orgs/${encodeURIComponent(id)}`, t),
  create: (
    t: string,
    body: { display_name: string; business_type: string; subtype?: string | null }
  ) => adminFetch<Org>("/v1/admin/orgs", t, json("POST", body)),
  setType: (
    t: string,
    id: string,
    body: { business_type: string; subtype?: string | null; reset_capabilities?: boolean }
  ) => adminFetch<Org>(`/v1/admin/orgs/${encodeURIComponent(id)}/type`, t, json("PUT", body)),
  setCapabilities: (t: string, id: string, capabilities: Record<string, boolean>) =>
    adminFetch<Org>(
      `/v1/admin/orgs/${encodeURIComponent(id)}/capabilities`,
      t,
      json("PUT", { capabilities })
    ),
  backfill: (t: string, dry_run: boolean) =>
    adminFetch<{ dry_run: boolean; count: number }>(
      "/v1/admin/orgs/backfill-from-merchants",
      t,
      json("POST", { dry_run })
    ),
};

/** Capabilities that differ from the type's defaults (shown as "changed by staff"). */
export function capabilityDiff(
  current: Record<string, boolean>,
  defaults: string[]
): { added: string[]; removed: string[] } {
  const on = Object.entries(current)
    .filter(([, v]) => v)
    .map(([k]) => k);
  return {
    added: on.filter((c) => !defaults.includes(c)).sort(),
    removed: defaults.filter((c) => !current[c]).sort(),
  };
}

export function typeLabel(types: BusinessType[] | undefined, code: string): string {
  return types?.find((t) => t.code === code)?.label ?? code.replace(/_/g, " ");
}
