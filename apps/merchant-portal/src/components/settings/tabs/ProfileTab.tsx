"use client";

import Link from "next/link";
import { startTransition, useEffect, useOptimistic, useState } from "react";
import { AddressAutocompleteInput, type BookingAddress } from "@porterchain/maps";
import Button from "@/components/ui/Button";
import { publicEnv } from "@/lib/env";
import { settingsApi, type AuditLogRow, type SettingsOverview } from "@/lib/settings";
import { formatDate } from "@/lib/utils";
import { Field } from "./Field";

export function ProfileTab({
  profile,
  onRefresh,
  getToken,
  orgId,
}: {
  profile: SettingsOverview["profile"];
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [form, setForm] = useState(profile);
  const [saved, setSaved] = useState(false);
  const [optimisticSaved, setOptimisticSaved] = useOptimistic(saved);
  const [billing, setBilling] = useState<BookingAddress>(() => ({
    formatted: String(profile.billing_address?.formatted ?? ""),
    postal:
      typeof profile.billing_address?.postal === "string"
        ? profile.billing_address.postal
        : undefined,
    placeId:
      typeof profile.billing_address?.place_id === "string"
        ? profile.billing_address.place_id
        : undefined,
  }));

  useEffect(() => {
    setForm(profile);
    setBilling({
      formatted: String(profile.billing_address?.formatted ?? ""),
      postal:
        typeof profile.billing_address?.postal === "string"
          ? profile.billing_address.postal
          : undefined,
      placeId:
        typeof profile.billing_address?.place_id === "string"
          ? profile.billing_address.place_id
          : undefined,
    });
  }, [profile]);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    startTransition(() => setOptimisticSaved(true));
    try {
      const token = await getToken();
      const patch: Parameters<typeof settingsApi.updateProfile>[1] = {
        company_name: form.company_name,
        email: form.email || undefined,
        phone: form.phone || undefined,
        website: form.website || undefined,
        industry: form.industry || undefined,
      };
      if ((form.legal_name || "") !== (profile.legal_name || "")) {
        patch.legal_name = form.legal_name || "";
      }
      await settingsApi.updateProfile(
        token,
        {
          ...patch,
          billing_address: billing.formatted
            ? {
                formatted: billing.formatted,
                postal: billing.postal,
                place_id: billing.placeId,
                lat: billing.lat,
                lng: billing.lng,
              }
            : undefined,
        },
        orgId
      );
      setSaved(true);
      await onRefresh();
      setTimeout(() => setSaved(false), 2000);
    } catch {
      setSaved(false);
    }
  };

  return (
    <div className="space-y-4">
      <CoverageCard coverage={profile.coverage} />
      <form
        onSubmit={(e) => void save(e)}
        className="space-y-4 rounded-2xl border border-primary/10 bg-white p-6"
      >
        <Field
          label="Company name"
          value={form.company_name}
          onChange={(v) => setForm({ ...form, company_name: v })}
        />
        <Field
          label="Legal name"
          value={form.legal_name || ""}
          onChange={(v) => setForm({ ...form, legal_name: v })}
        />
        <Field label="Email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} />
        <Field
          label="Phone"
          value={form.phone || ""}
          onChange={(v) => setForm({ ...form, phone: v })}
        />
        <Field
          label="Website"
          value={form.website || ""}
          onChange={(v) => setForm({ ...form, website: v })}
        />
        <Field
          label="Industry"
          value={form.industry || ""}
          onChange={(v) => setForm({ ...form, industry: v })}
        />
        <label className="block text-sm">
          <span className="font-medium">Billing address</span>
          <div className="mt-1">
            <AddressAutocompleteInput
              id="settings-billing"
              value={billing.formatted}
              onChange={(formatted) => setBilling({ ...billing, formatted })}
              onPlaceSelect={setBilling}
              apiKey={publicEnv.googleMapsApiKey}
              placeholder="Ontario billing address"
              fallbackClassName="w-full rounded-lg border px-3 py-2 text-sm"
            />
          </div>
        </label>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <p className="text-sm font-medium">Payment terms</p>
            <p className="mt-1 text-sm text-muted">{form.payment_terms.replace("_", " ")}</p>
          </div>
          <div>
            <p className="text-sm font-medium">Billing cycle</p>
            <p className="mt-1 text-sm text-muted">{form.billing_cycle || "—"}</p>
          </div>
        </div>
        {form.identity_meta?.updated_at && (
          <p className="text-xs text-muted">
            Last updated by {form.identity_meta.updated_by || "someone"}{" "}
            {new Date(form.identity_meta.updated_at).toLocaleString("en-CA", {
              timeZone: "America/Toronto",
            })}
          </p>
        )}
        <Button type="submit">Save profile</Button>
        {(optimisticSaved || saved) && <p className="text-sm text-green-700">Saved</p>}
      </form>
      <CompanyAuditCard getToken={getToken} orgId={orgId} />
      <p className="text-sm text-muted">
        Tickets and claims live under{" "}
        <Link href="/help" className="font-medium text-secondary underline">
          Help
        </Link>
        .
      </p>
    </div>
  );
}

function CompanyAuditCard({
  getToken,
  orgId,
}: {
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [rows, setRows] = useState<AuditLogRow[]>([]);
  const [count, setCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const token = await getToken();
        const snap = await settingsApi.auditLogs(token, orgId, 25);
        setRows(snap.recent_audit_logs || []);
        setCount(snap.audit_log_count || 0);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not load company activity");
      }
    })();
  }, [getToken, orgId]);

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Company activity</h2>
      <p className="mt-1 text-sm text-muted">
        Who changed what on this company file{count ? ` · ${count} events` : ""}.
      </p>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      {!error && rows.length === 0 ? (
        <p className="mt-4 text-sm text-muted">No activity yet.</p>
      ) : (
        <ul className="mt-4 space-y-2 text-sm">
          {rows.slice(0, 6).map((row) => (
            <li key={row.id} className="flex justify-between gap-4 border-b border-primary/5 py-2">
              <span className="font-medium text-primary">{row.summary}</span>
              <span className="shrink-0 text-xs text-muted">
                {row.created_at ? formatDate(row.created_at) : "—"}
              </span>
            </li>
          ))}
        </ul>
      )}
      {!error && rows.length > 6 && (
        <details className="text-sm">
          <summary className="cursor-pointer py-2 font-semibold text-secondary">
            Show {rows.length - 6} more
          </summary>
          <ul className="space-y-2">
            {rows.slice(6).map((row) => (
              <li
                key={row.id}
                className="flex justify-between gap-4 border-b border-primary/5 py-2"
              >
                <span className="font-medium text-primary">{row.summary}</span>
                <span className="shrink-0 text-xs text-muted">
                  {row.created_at ? formatDate(row.created_at) : "—"}
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}

function CoverageCard({ coverage }: { coverage?: SettingsOverview["profile"]["coverage"] }) {
  const snap = coverage ?? {
    service_area: "Ontario",
    service_area_note:
      "Pickup and drop-off must be in Ontario (postal codes starting with K, L, M, N, or P).",
    delivery_zones: [],
    assigned_vehicles: [],
    coverage_note:
      "PorterChain sends the vehicle. You book a class for the job — you do not manage a fleet.",
  };
  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Coverage</h2>
      <p className="mt-1 text-sm text-muted">{snap.coverage_note}</p>
      <p className="mt-2 text-xs text-muted">
        Live capacity is gated to the GTA ±150 km FSA tile. Addresses outside that tile (or without
        a rate) are rejected at quote — not silently booked.
      </p>
      <dl className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <dt className="text-sm font-medium">Service area</dt>
          <dd className="mt-1 text-sm text-primary">{snap.service_area}</dd>
          <p className="mt-1 text-xs text-muted">{snap.service_area_note}</p>
        </div>
        <div>
          <dt className="text-sm font-medium">Vehicles we send</dt>
          <dd className="mt-1 text-sm text-primary">
            {snap.assigned_vehicles.length
              ? snap.assigned_vehicles.map((v) => v.label).join(", ")
              : "Any class that fits the job"}
          </dd>
        </div>
        {snap.delivery_zones.length > 0 && (
          <div className="sm:col-span-2">
            <dt className="text-sm font-medium">Delivery zones</dt>
            <dd className="mt-1 text-sm text-primary">
              {snap.delivery_zones.map((z) => z.name || z.code).join(", ")}
            </dd>
          </div>
        )}
      </dl>
    </section>
  );
}
