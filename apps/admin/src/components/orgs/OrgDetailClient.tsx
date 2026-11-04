"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/crm/primitives";
import AdminPage from "@/components/layout/AdminPage";
import { OrgPricingPanel } from "@/components/pricing/RateCardClient";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { capabilityDiff, orgsApi, typeLabel, type BusinessTypes, type Org } from "@/lib/orgs";

export function OrgDetailClient({ orgId }: { orgId: string }) {
  const { getApiToken } = useAdminAuth();
  const [org, setOrg] = useState<Org | null>(null);
  const [types, setTypes] = useState<BusinessTypes | null>(null);
  const [type, setType] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    const t = await getApiToken();
    if (!t) return;
    const [o, ty] = await Promise.all([orgsApi.get(t, orgId), orgsApi.types(t)]);
    setOrg(o);
    setTypes(ty);
    setType(o.business_type);
  }, [getApiToken, orgId]);
  useEffect(() => {
    void load().catch((e) => setErr(String(e)));
  }, [load]);

  async function run(fn: (t: string) => Promise<Org>) {
    const t = await getApiToken();
    if (!t) return;
    try {
      setOrg(await fn(t));
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed");
    }
  }

  if (!org)
    return (
      <AdminPage title="Organisation">
        {err ? <p className="text-red-700">{err}</p> : "Loading…"}
      </AdminPage>
    );
  const defaults = Object.keys(org.capabilities).filter((c) => org.capabilities[c]);
  const diff = capabilityDiff(
    org.capabilities,
    types?.subtype_capabilities[org.subtype ?? ""] ?? defaults
  );

  return (
    <AdminPage
      title={`${org.display_name}`}
      description={`${org.public_id} · ${typeLabel(types?.business_types, org.business_type)} · ${org.status}`}
      actions={
        org.merchant_id ? (
          <Link
            className="text-sm text-secondary hover:underline"
            href={`/merchants/${org.merchant_id}`}
          >
            Open merchant
          </Link>
        ) : null
      }
    >
      {err ? <p className="text-sm text-red-700">{err}</p> : null}
      <section className="space-y-2 rounded-xl border border-primary/10 p-3">
        <h3 className="text-sm font-semibold">
          Business type{" "}
          {org.needs_review ? <span className="text-amber-700">(needs review)</span> : null}
        </h3>
        <div className="flex gap-2">
          <select
            aria-label="Business type"
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="rounded border px-2 py-1 text-sm"
          >
            {types?.business_types.map((b) => (
              <option key={b.code} value={b.code}>
                {b.label}
              </option>
            ))}
          </select>
          <Button
            onClick={() =>
              void run((t) =>
                orgsApi.setType(t, org.id, {
                  business_type: type,
                  reset_capabilities: type !== org.business_type,
                })
              )
            }
          >
            {org.needs_review && type === org.business_type ? "Confirm type" : "Save type"}
          </Button>
        </div>
      </section>
      <section className="space-y-2 rounded-xl border border-primary/10 p-3">
        <h3 className="text-sm font-semibold">Capabilities</h3>
        <div className="grid gap-1 sm:grid-cols-2 lg:grid-cols-3">
          {Object.entries(types?.capabilities ?? {}).map(([code, label]) => (
            <label key={code} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={Boolean(org.capabilities[code])}
                onChange={(e) =>
                  void run((t) => orgsApi.setCapabilities(t, org.id, { [code]: e.target.checked }))
                }
              />
              {label}
            </label>
          ))}
        </div>
        {diff.added.length || diff.removed.length ? (
          <p className="text-xs text-muted">
            Changed from pack: +{diff.added.join(", ") || "none"} / −
            {diff.removed.join(", ") || "none"}
          </p>
        ) : null}
      </section>
      <section className="space-y-1 rounded-xl border border-primary/10 p-3 text-sm">
        <h3 className="font-semibold">
          Operating profile {org.profile ? `v${org.profile.version}` : ""}
        </h3>
        <pre className="overflow-x-auto text-xs">{JSON.stringify(org.profile, null, 2)}</pre>
        <p className="text-xs text-muted">Documents: {org.documents.join(", ") || "none"}</p>
      </section>
      <OrgPricingPanel orgId={org.id} />
    </AdminPage>
  );
}
