"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { cn } from "@porterchain/ui/utils";
import { AddressAutocompleteInput, type BookingAddress } from "@porterchain/maps";
import { publicEnv } from "@/lib/env";
import { getSystemLinks } from "@/lib/system-links";
import GoogleMapsProvider from "@/components/maps/GoogleMapsProvider";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";
import { ImpersonateModal } from "@/components/settings/panels/users/ImpersonateModal";
import {
  merchants,
  merchantActionMessage,
  BILLING_CYCLES,
  RETAIL_VEHICLE_OPTIONS,
  vehicleClassLabel,
  type MerchantDetail,
  type MerchantTeamUser,
} from "@/lib/merchants";
import MerchantBillingContactsCard from "@/components/merchants/MerchantBillingContactsCard";
import MerchantPrivacyCard from "@/components/merchants/MerchantPrivacyCard";
import { Badge, Button, Field, Input, Select, SectionCard } from "@/components/crm/primitives";
import { dateTime, money, titleCase } from "@/lib/crmFormat";

/** Seats that can complete Stripe Connect / COD (Owner or Manager). */
const MERCHANT_BILLING_ROLES = new Set(["merchant_owner", "merchant_admin"]);

function pickBillingSeat(team: MerchantTeamUser[] | null | undefined): MerchantTeamUser | null {
  const active = (team ?? []).filter((u) => u.is_active);
  const owner = active.find((u) => u.role === "merchant_owner");
  if (owner) return owner;
  return active.find((u) => MERCHANT_BILLING_ROLES.has(u.role)) ?? null;
}

const TERMS = ["IMMEDIATE", "NET_7", "NET_14", "NET_15", "NET_30", "NET_45", "CUSTOM"];
const SUPPORT_TIERS = ["standard", "priority", "enterprise"] as const;
const CA_TAX_REGIONS = [
  "AB",
  "BC",
  "MB",
  "NB",
  "NL",
  "NS",
  "NT",
  "NU",
  "ON",
  "PE",
  "QC",
  "SK",
  "YT",
];

function serviceAreaFromMerchant(m: MerchantDetail): string {
  const fromProfile =
    typeof m.profile?.service_area === "string" ? m.profile.service_area.trim() : "";
  return fromProfile || m.coverage?.service_area || m.service_area || "Ontario";
}

function zonesFromMerchant(m: MerchantDetail): string {
  return (m.delivery_zones ?? [])
    .map((z) => String(z))
    .filter(Boolean)
    .join(", ");
}

function billingFromMerchant(m: MerchantDetail): BookingAddress {
  const raw = (m.billing_address ?? {}) as Record<string, unknown>;
  return {
    formatted: String(raw.formatted ?? ""),
    postal: typeof raw.postal === "string" ? raw.postal : undefined,
    lat: typeof raw.lat === "number" ? raw.lat : undefined,
    lng: typeof raw.lng === "number" ? raw.lng : undefined,
    placeId: typeof raw.place_id === "string" ? raw.place_id : undefined,
  };
}

export function SettingsTab({ m, onSaved }: { m: MerchantDetail; onSaved: () => void }) {
  const { getApiToken } = useAdminAuth();
  const { profile } = useAdminProfile();
  const canImpersonate = (profile?.role || "").toLowerCase() === "super_admin";
  const { data: team } = useApiData((t) => merchants.team(t, m.id), [m.id], {
    key: `merchant-team-settings-${m.id}`,
  });
  const billingSeat = useMemo(() => pickBillingSeat(team), [team]);
  const [impersonateOpen, setImpersonateOpen] = useState(false);
  const merchantPortalBase =
    getSystemLinks().find((l) => l.id === "merchant")?.href ?? "https://merchant.porterchain.com";
  const [companyName, setCompanyName] = useState(m.company_name);
  const [legalName, setLegalName] = useState(m.legal_name ?? "");
  const [email, setEmail] = useState(m.email ?? "");
  const [website, setWebsite] = useState(m.website ?? "");
  const [industry, setIndustry] = useState(m.industry ?? "");
  const [terms, setTerms] = useState(m.payment_terms);
  const [creditDollars, setCreditDollars] = useState(
    m.credit_limit_cents != null ? (m.credit_limit_cents / 100).toFixed(2) : ""
  );
  const [cycle, setCycle] = useState(m.billing_cycle || "MONTHLY");
  const [supportTier, setSupportTier] = useState(m.support_tier || "standard");
  const [phone, setPhone] = useState(m.phone ?? "");
  const [hst, setHst] = useState(m.hst_number ?? "");
  const [bn, setBn] = useState(m.business_number ?? "");
  const [taxExempt, setTaxExempt] = useState(Boolean(m.tax_exempt));
  const [taxRegion, setTaxRegion] = useState(m.tax_region || "ON");
  const [stripeOn, setStripeOn] = useState(Boolean(m.stripe_enabled));
  const [codOn, setCodOn] = useState(Boolean(m.cod_enabled));
  const [prefs, setPrefs] = useState<string[]>(m.preferred_vehicles ?? []);
  const [serviceArea, setServiceArea] = useState(() => serviceAreaFromMerchant(m));
  const [zonesText, setZonesText] = useState(() => zonesFromMerchant(m));
  const [billing, setBilling] = useState<BookingAddress>(() => billingFromMerchant(m));
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    setCompanyName(m.company_name);
    setLegalName(m.legal_name ?? "");
    setEmail(m.email ?? "");
    setWebsite(m.website ?? "");
    setIndustry(m.industry ?? "");
    setTerms(m.payment_terms);
    setCreditDollars(m.credit_limit_cents != null ? (m.credit_limit_cents / 100).toFixed(2) : "");
    setCycle(m.billing_cycle || "MONTHLY");
    setSupportTier(m.support_tier || "standard");
    setPhone(m.phone ?? "");
    setHst(m.hst_number ?? "");
    setBn(m.business_number ?? "");
    setTaxExempt(Boolean(m.tax_exempt));
    setTaxRegion(m.tax_region || "ON");
    setStripeOn(Boolean(m.stripe_enabled));
    setCodOn(Boolean(m.cod_enabled));
    setPrefs(m.preferred_vehicles ?? []);
    setServiceArea(serviceAreaFromMerchant(m));
    setZonesText(zonesFromMerchant(m));
    setBilling(billingFromMerchant(m));
  }, [m]);

  function togglePref(id: string) {
    setPrefs((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  async function save() {
    setBusy(true);
    setSaveError(null);
    try {
      const token = await getApiToken();
      const body: Parameters<typeof merchants.update>[2] = {
        company_name: companyName.trim(),
        email: email.trim() || undefined,
        website: website.trim() || undefined,
        industry: industry.trim() || undefined,
        payment_terms: terms,
        credit_limit_cents: Math.round(Number(creditDollars || 0) * 100),
        billing_cycle: cycle,
        support_tier: supportTier as "standard" | "priority" | "enterprise",
        preferred_vehicles: prefs,
        delivery_zones: zonesText
          .split(/[,\n]/)
          .map((code) => code.trim())
          .filter(Boolean),
        service_area: serviceArea.trim(),
        phone: phone.trim(),
        stripe_enabled: stripeOn,
        cod_enabled: codOn,
        billing_address: billing.formatted.trim()
          ? {
              formatted: billing.formatted.trim(),
              postal: billing.postal,
              lat: billing.lat,
              lng: billing.lng,
              place_id: billing.placeId,
            }
          : {},
      };
      if ((legalName.trim() || "") !== (m.legal_name || "")) {
        body.legal_name = legalName.trim();
      }
      if (hst.trim() !== (m.hst_number || "")) {
        body.hst_number = hst.trim();
      }
      if ((bn.trim() || "") !== (m.business_number || "")) {
        body.business_number = bn.trim();
      }
      if (taxExempt !== Boolean(m.tax_exempt)) {
        body.tax_exempt = taxExempt;
      }
      if ((taxRegion.trim() || "ON") !== (m.tax_region || "ON")) {
        body.tax_region = taxRegion.trim() || "ON";
      }
      await merchants.update(token, m.id, body);
      setSaved(true);
      onSaved();
      setTimeout(() => setSaved(false), 2500);
    } catch (e) {
      setSaved(false);
      setSaveError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <p className="text-sm text-muted">
        Org config for this company. Pricing lives on the Pricing tab. Seats live under People.
      </p>
      <SectionCard title="Company identity">
        <div className="grid grid-cols-2 gap-4 p-5">
          <div className="col-span-2">
            <Field label="Company name">
              <Input value={companyName} onChange={(e) => setCompanyName(e.target.value)} />
            </Field>
          </div>
          <Field label="Legal name">
            <Input value={legalName} onChange={(e) => setLegalName(e.target.value)} />
          </Field>
          <Field label="Company email">
            <Input value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Field label="Website">
            <Input value={website} onChange={(e) => setWebsite(e.target.value)} />
          </Field>
          <Field label="Industry">
            <Input value={industry} onChange={(e) => setIndustry(e.target.value)} />
          </Field>
          <Field label="Phone">
            <Input value={phone} onChange={(e) => setPhone(e.target.value)} />
          </Field>
          <div className="col-span-2">
            <p className="mb-1 text-xs font-medium text-primary/70">Billing address</p>
            <GoogleMapsProvider>
              <AddressAutocompleteInput
                id={`admin-merchant-billing-${m.id}`}
                value={billing.formatted}
                onChange={(formatted) => setBilling({ ...billing, formatted })}
                onPlaceSelect={setBilling}
                apiKey={publicEnv.googleMapsApiKey}
                placeholder="Ontario billing address"
                fallbackClassName="w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
              />
            </GoogleMapsProvider>
          </div>
        </div>
      </SectionCard>
      <SectionCard title="Commercial terms">
        <div className="grid grid-cols-2 gap-4 p-5">
          <Field label="Payment terms">
            <Select value={terms} onChange={(e) => setTerms(e.target.value)}>
              {TERMS.map((t) => (
                <option key={t} value={t}>
                  {titleCase(t)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Billing cycle">
            <Select value={cycle} onChange={(e) => setCycle(e.target.value)}>
              {BILLING_CYCLES.map((c) => (
                <option key={c} value={c}>
                  {titleCase(c)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Support tier">
            <Select value={supportTier} onChange={(e) => setSupportTier(e.target.value)}>
              {SUPPORT_TIERS.map((tier) => (
                <option key={tier} value={tier}>
                  {titleCase(tier)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Credit limit (CAD)">
            <Input
              type="number"
              step="0.01"
              value={creditDollars}
              onChange={(e) => setCreditDollars(e.target.value)}
            />
          </Field>
          <div className="col-span-2 space-y-3">
            <label className="flex items-center gap-2 text-sm text-primary">
              <input
                type="checkbox"
                checked={stripeOn}
                onChange={(e) => setStripeOn(e.target.checked)}
              />
              Stripe checkout enabled (card / IMMEDIATE path)
            </label>
            <label className="flex items-center gap-2 text-sm text-primary">
              <input type="checkbox" checked={codOn} onChange={(e) => setCodOn(e.target.checked)} />
              Cash on delivery (requires Stripe Connect on the merchant billing page)
            </label>
            {m.stripe_connect_account_id ? (
              <p className="text-xs text-muted">Connect account {m.stripe_connect_account_id}</p>
            ) : (
              <div className="space-y-2 text-xs text-muted">
                <p>
                  No Connect account yet. The merchant Owner completes Stripe Connect under Billing
                  → COD (staff never uses their password).
                </p>
                {canImpersonate && billingSeat ? (
                  <Button
                    variant="outline"
                    className="text-xs"
                    onClick={() => setImpersonateOpen(true)}
                  >
                    Open Billing → COD as {billingSeat.role_label || "Owner"}
                  </Button>
                ) : canImpersonate && !billingSeat ? (
                  <p className="text-amber-800">
                    No active Owner/Manager seat — add one on the Team tab first.
                  </p>
                ) : (
                  <a
                    href={`${merchantPortalBase}/billing?tab=cod`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-secondary underline"
                  >
                    Portal Billing → COD (your own merchant seat)
                  </a>
                )}
              </div>
            )}
            {impersonateOpen && billingSeat ? (
              <ImpersonateModal
                open
                targetType="merchant"
                targetId={billingSeat.id}
                targetLabel={billingSeat.email}
                getApiToken={getApiToken}
                nextPath="/billing?tab=cod"
                onClose={() => setImpersonateOpen(false)}
              />
            ) : null}
          </div>
        </div>
      </SectionCard>
      <SectionCard title="Tax & legal">
        <div className="grid grid-cols-2 gap-4 p-5">
          <Field label="HST / GST number">
            <Input
              value={hst}
              onChange={(e) => setHst(e.target.value)}
              placeholder="123456789RT0001"
            />
          </Field>
          <Field label="Business number">
            <Input value={bn} onChange={(e) => setBn(e.target.value)} placeholder="123456789" />
          </Field>
          <Field label="Tax region">
            <Select value={taxRegion} onChange={(e) => setTaxRegion(e.target.value)}>
              {CA_TAX_REGIONS.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </Select>
          </Field>
          <label className="flex items-center gap-2 text-sm text-primary">
            <input
              type="checkbox"
              checked={taxExempt}
              onChange={(e) => setTaxExempt(e.target.checked)}
            />
            Tax exempt
          </label>
        </div>
      </SectionCard>
      <SectionCard title="Coverage we send">
        <div className="grid grid-cols-2 gap-4 p-5">
          <div className="col-span-2">
            <Field label="Service area">
              <Input
                value={serviceArea}
                onChange={(e) => setServiceArea(e.target.value)}
                placeholder="Ontario"
              />
            </Field>
            <p className="mt-1 text-xs text-muted">
              Shown read-only in the merchant portal. Pickup and drop-off stay Ontario (K, L, M, N,
              P).
            </p>
          </div>
          <div className="col-span-2">
            <Field label="Delivery zone codes">
              <Input
                value={zonesText}
                onChange={(e) => setZonesText(e.target.value)}
                placeholder="gta_core, gta_west"
              />
            </Field>
            <p className="mt-1 text-xs text-muted">Comma-separated pricing zone codes.</p>
          </div>
        </div>
      </SectionCard>
      <SectionCard title="Assigned vehicles we send">
        <div className="flex flex-wrap gap-2 p-5">
          {RETAIL_VEHICLE_OPTIONS.map((v) => {
            const on = prefs.includes(v);
            return (
              <button
                key={v}
                type="button"
                onClick={() => togglePref(v)}
                className={cn(
                  "rounded-xl border px-3 py-1.5 text-sm font-medium transition",
                  on
                    ? "border-secondary bg-secondary/10 text-secondary"
                    : "border-primary/15 text-muted hover:bg-gray-bg"
                )}
              >
                {vehicleClassLabel(v)}
              </button>
            );
          })}
          <p className="w-full text-xs text-muted">
            Vehicles PorterChain sends for this merchant. They book a class for the job — they do
            not manage a fleet. Soft-ranks booking recommendations; must match the retail catalog.
          </p>
        </div>
      </SectionCard>
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={save} disabled={busy}>
          Save changes
        </Button>
        {saved && <span className="text-sm text-green-600">Saved</span>}
        {saveError && <span className="text-sm text-red-600">{saveError}</span>}
        {m.tax_legal_meta?.updated_at ? (
          <span className="text-xs text-muted">
            Tax & legal last updated by {m.tax_legal_meta.updated_by || "someone"}{" "}
            {dateTime(m.tax_legal_meta.updated_at)}
          </span>
        ) : null}
      </div>
      <MerchantBillingContactsCard id={m.id} />
      {(m.documents?.length ?? 0) > 0 && (
        <SectionCard title="Documents on file">
          <ul className="divide-y divide-primary/5">
            {m.documents?.map((doc) => (
              <li key={doc.id} className="flex justify-between gap-3 px-5 py-3 text-sm">
                <span>
                  <span className="font-medium text-primary">{doc.name}</span>
                  <span className="ml-2 text-muted">{doc.type || "other"}</span>
                  {doc.reference ? <span className="ml-2 text-muted">{doc.reference}</span> : null}
                </span>
              </li>
            ))}
          </ul>
        </SectionCard>
      )}
      <SubsidiariesCard merchantId={m.id} parentId={m.parent_merchant_id} onChanged={onSaved} />
      <MerchantPrivacyCard id={m.id} />
      <DangerZone m={m} onSaved={onSaved} />
    </div>
  );
}

export function SubsidiariesCard({
  merchantId,
  parentId,
  onChanged,
}: {
  merchantId: string;
  parentId?: string | null;
  onChanged?: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const { data, refetch } = useApiData((t) => merchants.subsidiaries(t, merchantId), [merchantId], {
    key: `merchant-subsidiaries-${merchantId}`,
  });
  const { data: parentDetail } = useApiData(
    (t) => (parentId ? merchants.detail(t, parentId) : Promise.resolve(null)),
    [parentId],
    { key: `merchant-parent-${parentId || "none"}`, enabled: Boolean(parentId) }
  );
  const [parentInput, setParentInput] = useState(parentId ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const rows = data ?? [];

  useEffect(() => {
    setParentInput(parentId ?? "");
  }, [parentId]);

  async function saveParent(next: string | null) {
    setBusy(true);
    setError(null);
    try {
      const token = await getApiToken();
      // Empty string clears parent (API treats null as "omit field").
      await merchants.update(token, merchantId, {
        parent_merchant_id: next && next.trim() ? next.trim() : "",
      });
      void refetch();
      onChanged?.();
    } catch (e) {
      setError(merchantActionMessage(e, "Could not update parent company"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <SectionCard title="Related companies">
      <div className="space-y-3 px-5 py-4 text-sm">
        <div className="space-y-2">
          <p className="text-xs text-muted">Parent company (UUID). Clear to detach.</p>
          {parentId ? (
            <p className="text-muted">
              Current parent{" "}
              <Link href={`/merchants/${parentId}`} className="font-medium text-secondary">
                {(parentDetail as MerchantDetail | null)?.company_name ||
                  `${parentId.slice(0, 8)}…`}
              </Link>
            </p>
          ) : null}
          <div className="flex flex-wrap items-center gap-2">
            <Input
              value={parentInput}
              onChange={(e) => setParentInput(e.target.value)}
              placeholder="Parent merchant id"
              className="min-w-[16rem] flex-1"
            />
            <Button
              disabled={busy || !parentInput.trim() || parentInput.trim() === merchantId}
              onClick={() => void saveParent(parentInput.trim())}
            >
              {busy ? "Saving…" : "Attach"}
            </Button>
            {parentId ? (
              <Button variant="outline" disabled={busy} onClick={() => void saveParent(null)}>
                Clear
              </Button>
            ) : null}
          </div>
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
        </div>
        {rows.map((row) => (
          <Link
            key={row.merchant_id}
            href={`/merchants/${row.merchant_id}`}
            className="flex items-center justify-between rounded-lg px-2 py-1.5 hover:bg-gray-bg"
          >
            <span className="font-medium text-primary">{row.company_name}</span>
            <span className="text-xs text-muted">{titleCase(row.status)}</span>
          </Link>
        ))}
        {!parentId && rows.length === 0 ? (
          <p className="text-xs text-muted">No subsidiaries linked yet.</p>
        ) : null}
      </div>
    </SectionCard>
  );
}

export function DangerZone({ m, onSaved }: { m: MerchantDetail; onSaved: () => void }) {
  const { getApiToken } = useAdminAuth();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const closed = m.status === "CLOSED";
  const owed = m.outstanding_balance_cents || 0;

  async function run(action: string, fn: () => Promise<void>) {
    setBusy(action);
    setError(null);
    try {
      await fn();
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <SectionCard title="Close or convert">
      <div className="space-y-3 p-5 text-sm">
        <p className="text-muted">
          Closing turns off the merchant portal. Orders and invoices stay on this company file.
          Convert opens a retail customer record for the owner email without moving shipment
          history.
        </p>
        {owed > 0 && (
          <p className="rounded-lg bg-amber-50 px-3 py-2 text-amber-900">
            Outstanding AR: {money(owed)}. Close is blocked until this is collected. Convert can
            write it off.
          </p>
        )}
        {error && <p className="text-red-600">{error}</p>}
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            disabled={closed || busy !== null}
            onClick={() => {
              const reason = window.prompt("Reason for closing this merchant account?");
              if (!reason?.trim()) return;
              void run("close", async () => {
                const token = await getApiToken();
                await merchants.close(token, m.id, reason.trim());
              });
            }}
          >
            {busy === "close" ? "Closing…" : "Close account"}
          </Button>
          <Button
            variant="outline"
            disabled={closed || busy !== null}
            onClick={() => {
              if (
                !window.confirm(
                  "Convert this merchant to a retail customer? Portal seats will be revoked. Historical orders stay on this merchant."
                )
              ) {
                return;
              }
              const writeOff =
                owed > 0 &&
                window.confirm(`Write off ${money(owed)} outstanding AR so convert can proceed?`);
              if (owed > 0 && !writeOff) return;
              void run("convert", async () => {
                const token = await getApiToken();
                await merchants.convertToCustomer(token, m.id, {
                  owner_email: m.email || undefined,
                  write_off_ar: Boolean(writeOff),
                });
              });
            }}
          >
            {busy === "convert" ? "Converting…" : "Convert to retail customer"}
          </Button>
          {closed && (
            <Button
              variant="outline"
              disabled={busy !== null}
              onClick={() => {
                if (
                  !window.confirm(
                    "Erase contact details for this closed merchant? Order numbers and invoice amounts are kept."
                  )
                ) {
                  return;
                }
                void run("privacy", async () => {
                  const token = await getApiToken();
                  await merchants.executePrivacy(token, m.id);
                });
              }}
            >
              {busy === "privacy" ? "Erasing…" : "Execute privacy erasure"}
            </Button>
          )}
        </div>
      </div>
    </SectionCard>
  );
}
