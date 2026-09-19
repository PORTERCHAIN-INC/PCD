"use client";

import CompanyCompletenessBanner from "@/components/onboarding/CompanyCompletenessBanner";
import MapsMissingBanner from "@/components/maps/MapsMissingBanner";
import Button from "@/components/ui/Button";
import { EmptyState } from "@porterchain/ui/empty-state";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { notificationsApi } from "@/lib/notifications";
import {
  settingsApi,
  type AuditLogRow,
  type BrandingPrefs,
  type BusinessDocument,
  type NotificationPrefs,
  type PrivacyStatus,
  type QuietHours,
  type SettingsOverview,
} from "@/lib/settings";
import { formatDate } from "@/lib/utils";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AddressAutocompleteInput, type BookingAddress } from "@porterchain/maps";
import { publicEnv } from "@/lib/env";
import Link from "next/link";

type Tab =
  | "profile"
  | "recipients"
  | "locations"
  | "notifications"
  | "branding"
  | "tax"
  | "documents"
  | "privacy";

const TABS: { id: Tab; label: string; module?: string }[] = [
  { id: "profile", label: "Business profile" },
  { id: "locations", label: "Locations" },
  { id: "recipients", label: "Delivery contacts" },
  { id: "notifications", label: "Alert preferences" },
  { id: "branding", label: "Branding" },
  { id: "tax", label: "Tax" },
  { id: "documents", label: "Documents" },
  { id: "privacy", label: "Privacy" },
];

const MOVED_TABS: Record<string, { href: string; label: string }> = {
  billing: { href: "/billing?tab=contacts", label: "Billing contacts" },
  contract: { href: "/billing?tab=rates", label: "Rate card" },
};

function parseSettingsTab(value: string | null): Tab {
  if (value && TABS.some((t) => t.id === value)) return value as Tab;
  return "profile";
}

export default function SettingsClient() {
  const { getApiToken, orgId, isLoaded, isSignedIn, refreshSession, modules } = useMerchantAuth();
  const visibleTabs = useMemo(
    () => TABS.filter((t) => !t.module || modules.includes(t.module)),
    [modules]
  );
  const searchParams = useSearchParams();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>(() => parseSettingsTab(searchParams.get("tab")));
  const [data, setData] = useState<SettingsOverview | null>(null);
  const [recipients, setRecipients] = useState<
    Array<{ id: string; name: string; email?: string | null; phone?: string | null }>
  >([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!isSignedIn) return;
    setError(null);
    try {
      const token = await getApiToken();
      const [ov, recips] = await Promise.all([
        settingsApi.overview(token, orgId),
        settingsApi.recipients(token, orgId),
      ]);
      setData(ov);
      setRecipients(recips);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load settings");
    }
  }, [getApiToken, orgId, isSignedIn]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    void load();
  }, [isLoaded, isSignedIn, load]);

  useEffect(() => {
    const raw = searchParams.get("tab");
    const moved = raw ? MOVED_TABS[raw] : null;
    if (moved) {
      router.replace(moved.href);
      return;
    }
    const next = parseSettingsTab(raw);
    const allowed = visibleTabs.some((t) => t.id === next)
      ? next
      : (visibleTabs[0]?.id ?? "profile");
    setTab(allowed);
  }, [searchParams, visibleTabs, router]);

  function gotoTab(id: Tab) {
    setTab(id);
    router.replace(`/settings?tab=${id}`, { scroll: false });
  }

  if (!isLoaded || !data) {
    if (error) {
      return <EmptyState title="Could not load settings" hint={error} />;
    }
    return <PageSkeleton rows={5} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-primary sm:text-2xl">Settings</h1>
        <p className="mt-1 text-sm text-muted">
          Company file, locations, tax, branding, and privacy. Invoices and the rate card are under{" "}
          <Link href="/billing" className="font-medium text-secondary underline">
            Billing
          </Link>
          . Seats are under{" "}
          <Link href="/team" className="font-medium text-secondary underline">
            Team
          </Link>
          .
        </p>
      </div>

      <CompanyCompletenessBanner completeness={data.completeness} />
      <MapsMissingBanner />

      {error && <p className="text-sm text-red-600">{error}</p>}

      <nav
        className="ops-tab-rail rounded-2xl border border-primary/10 bg-white"
        aria-label="Settings sections"
      >
        {visibleTabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => gotoTab(t.id)}
            className={`min-h-10 shrink-0 rounded-xl px-3 py-1.5 text-sm font-medium whitespace-nowrap ${
              tab === t.id ? "bg-primary text-white" : "text-muted hover:bg-primary/5"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "profile" && (
        <ProfileTab profile={data.profile} onRefresh={load} getToken={getApiToken} orgId={orgId} />
      )}
      {tab === "recipients" && (
        <RecipientsTab
          recipients={recipients}
          onRefresh={load}
          getToken={getApiToken}
          orgId={orgId}
        />
      )}
      {tab === "locations" && (
        <LocationsTab data={data} onRefresh={load} getToken={getApiToken} orgId={orgId} />
      )}
      {tab === "notifications" && (
        <NotificationsTab
          prefs={data.notifications}
          quietHours={data.quiet_hours}
          onRefresh={load}
          getToken={getApiToken}
          orgId={orgId}
        />
      )}
      {tab === "branding" && (
        <BrandingTab
          branding={data.branding}
          onRefresh={load}
          getToken={getApiToken}
          orgId={orgId}
          onSaved={() => void refreshSession()}
        />
      )}
      {tab === "tax" && (
        <TaxTab tax={data.tax} onRefresh={load} getToken={getApiToken} orgId={orgId} />
      )}
      {tab === "documents" && (
        <DocumentsTab
          documents={data.documents ?? []}
          onRefresh={load}
          getToken={getApiToken}
          orgId={orgId}
        />
      )}
      {tab === "privacy" && <PrivacyTab getToken={getApiToken} orgId={orgId} />}
    </div>
  );
}

function RecipientsTab({
  recipients,
  onRefresh,
  getToken,
  orgId,
}: {
  recipients: Array<{ id: string; name: string; email?: string | null; phone?: string | null }>;
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");

  const add = async () => {
    if (!name.trim()) return;
    const token = await getToken();
    await settingsApi.addRecipient(
      token,
      { name, email: email || undefined, phone: phone || undefined },
      orgId
    );
    setName("");
    setEmail("");
    setPhone("");
    await onRefresh();
  };

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Delivery contacts</h2>
      <p className="mt-1 text-sm text-muted">
        Saved consignees for booking and CSV import. Portal seats live on{" "}
        <Link href="/team" className="font-medium text-secondary underline">
          Team
        </Link>
        .
      </p>
      <ul className="mt-4 space-y-2 text-sm">
        {recipients.length === 0 && <li className="text-muted">No recipients yet</li>}
        {recipients.map((r) => (
          <li key={r.id} className="flex justify-between border-b border-primary/5 py-2">
            <span>
              <span className="font-medium">{r.name}</span>
              {r.email && <span className="ml-2 text-muted">{r.email}</span>}
            </span>
            {r.phone && <span className="text-muted">{r.phone}</span>}
            <button
              type="button"
              className="text-xs text-red-600"
              onClick={() =>
                void getToken().then((t) =>
                  settingsApi.deleteRecipient(t, r.id, orgId).then(onRefresh)
                )
              }
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
      <div className="mt-4 flex flex-wrap gap-2">
        <input
          className="rounded-lg border px-3 py-2 text-sm"
          placeholder="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          className="rounded-lg border px-3 py-2 text-sm"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="rounded-lg border px-3 py-2 text-sm"
          placeholder="Phone"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
        <Button size="sm" onClick={() => void add()}>
          Add recipient
        </Button>
      </div>
    </section>
  );
}

function ProfileTab({
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
        {saved && <p className="text-sm text-green-700">Saved</p>}
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
          {rows.map((row) => (
            <li key={row.id} className="flex justify-between gap-4 border-b border-primary/5 py-2">
              <span className="font-medium text-primary">{row.summary}</span>
              <span className="shrink-0 text-xs text-muted">
                {row.created_at ? formatDate(row.created_at) : "—"}
              </span>
            </li>
          ))}
        </ul>
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

function LocationsTab({
  data,
  onRefresh,
  getToken,
  orgId,
}: {
  data: SettingsOverview;
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [pickupLabel, setPickupLabel] = useState("");
  const [pickup, setPickup] = useState<BookingAddress>({ formatted: "" });

  const addPickup = async () => {
    if (!pickupLabel.trim() || !pickup.formatted.trim()) return;
    const token = await getToken();
    await settingsApi.addPickup(
      token,
      {
        label: pickupLabel,
        formatted: pickup.formatted,
        postal: pickup.postal,
        lat: pickup.lat,
        lng: pickup.lng,
        place_id: pickup.placeId,
        is_default: data.pickup_locations.length === 0,
      },
      orgId
    );
    setPickupLabel("");
    setPickup({ formatted: "" });
    await onRefresh();
  };

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Pickup locations</h2>
      <p className="mt-1 text-sm text-muted">
        The default location is pre-filled when you book. Addresses are the company record — not a
        separate warehouse list.
      </p>
      <ul className="mt-4 space-y-2 text-sm">
        {data.pickup_locations.map((p) => (
          <li key={p.id} className="flex justify-between gap-2">
            <span>
              <span className="font-medium">{p.label}</span>
              {p.is_default && (
                <span className="ml-2 rounded-full bg-secondary/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-secondary">
                  Default
                </span>
              )}
              <span className="block text-muted">{p.formatted}</span>
            </span>
            <span className="flex shrink-0 items-center gap-2">
              {!p.is_default && (
                <button
                  type="button"
                  className="text-xs text-secondary"
                  onClick={() =>
                    void getToken().then((t) =>
                      settingsApi.setDefaultPickup(t, p.id, orgId).then(onRefresh)
                    )
                  }
                >
                  Set default
                </button>
              )}
              <button
                type="button"
                className="text-xs text-red-600"
                onClick={() =>
                  void getToken().then((t) =>
                    settingsApi.deletePickup(t, p.id, orgId).then(onRefresh)
                  )
                }
              >
                Remove
              </button>
            </span>
          </li>
        ))}
      </ul>
      <div className="mt-4 space-y-2">
        <input
          className="w-full rounded-lg border px-3 py-2 text-sm"
          placeholder="Label (e.g. Main warehouse)"
          value={pickupLabel}
          onChange={(e) => setPickupLabel(e.target.value)}
        />
        <AddressAutocompleteInput
          id="settings-pickup"
          value={pickup.formatted}
          onChange={(formatted) => setPickup({ ...pickup, formatted })}
          onPlaceSelect={setPickup}
          apiKey={publicEnv.googleMapsApiKey}
          placeholder="Ontario address"
          fallbackClassName="w-full rounded-lg border px-3 py-2 text-sm"
        />
        <Button size="sm" onClick={() => void addPickup()}>
          Add location
        </Button>
      </div>
    </section>
  );
}

function hourLabel(hour: number): string {
  const period = hour >= 12 ? "pm" : "am";
  const hour12 = hour % 12 === 0 ? 12 : hour % 12;
  return `${hour12}:00 ${period}`;
}

const DEFAULT_QUIET: QuietHours = {
  quiet_hours_enabled: false,
  quiet_start_hour: 22,
  quiet_end_hour: 7,
  timezone: "America/Toronto",
};

function NotificationsTab({
  prefs,
  quietHours,
  onRefresh,
  getToken,
  orgId,
}: {
  prefs: NotificationPrefs;
  quietHours?: QuietHours;
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [quiet, setQuiet] = useState<QuietHours>(quietHours ?? DEFAULT_QUIET);
  const [quietBusy, setQuietBusy] = useState(false);
  const [quietMessage, setQuietMessage] = useState<string | null>(null);

  useEffect(() => {
    if (quietHours) setQuiet(quietHours);
  }, [quietHours]);

  const toggle = async (key: keyof NotificationPrefs, value: boolean) => {
    const token = await getToken();
    await settingsApi.updateNotifications(token, { [key]: value }, orgId);
    await onRefresh();
  };

  const toggleChannel = async (channel: "email" | "in_app", value: boolean) => {
    const token = await getToken();
    await settingsApi.updateNotifications(
      token,
      { channels: { ...prefs.channels, [channel]: value } },
      orgId
    );
    await onRefresh();
  };

  const saveQuiet = async (next: QuietHours) => {
    setQuietBusy(true);
    setQuietMessage(null);
    try {
      const token = await getToken();
      const saved = await notificationsApi.updateQuietHours(
        token,
        { ...next, timezone: "America/Toronto" },
        orgId
      );
      setQuiet(saved);
      await onRefresh();
      setQuietMessage("Quiet hours saved.");
    } catch (e) {
      setQuietMessage(e instanceof Error ? e.message : "Could not save quiet hours");
    } finally {
      setQuietBusy(false);
    }
  };

  const items: { key: keyof NotificationPrefs; label: string }[] = [
    { key: "order_booked", label: "Order booked" },
    { key: "order_delivered", label: "Order delivered" },
    { key: "order_failed", label: "Failed delivery" },
    { key: "invoice_generated", label: "Invoice generated" },
    { key: "payment_received", label: "Payment received" },
    { key: "claim_updates", label: "Claim updates" },
    { key: "support_replies", label: "Support replies" },
    { key: "weekly_summary", label: "Weekly summary" },
  ];

  const channels = prefs.channels ?? { email: true, in_app: true };

  return (
    <div className="space-y-5">
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Notification preferences</h2>
        <p className="mt-1 text-xs text-muted">
          Changes apply to this company (email and in-app). SMS stays off until enabled.
        </p>
        <div className="mt-4 flex flex-wrap gap-6 border-b border-primary/8 pb-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={Boolean(channels.email)}
              onChange={(e) => void toggleChannel("email", e.target.checked)}
            />
            Email
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={Boolean(channels.in_app)}
              onChange={(e) => void toggleChannel("in_app", e.target.checked)}
            />
            In-app
          </label>
        </div>
        <ul className="mt-4 space-y-3">
          {items.map((item) => (
            <li key={item.key} className="flex items-center justify-between text-sm">
              <span>{item.label}</span>
              <input
                type="checkbox"
                checked={Boolean(prefs[item.key])}
                onChange={(e) => void toggle(item.key, e.target.checked)}
              />
            </li>
          ))}
        </ul>
      </section>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Quiet hours</h2>
        <p className="mt-1 text-sm text-muted">
          Pause push alerts overnight. Email and in-app still arrive. Urgent alerts still go
          through. Times are Eastern Time (Toronto).
        </p>
        <label className="mt-4 flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={quiet.quiet_hours_enabled}
            disabled={quietBusy}
            onChange={(e) => void saveQuiet({ ...quiet, quiet_hours_enabled: e.target.checked })}
          />
          Pause push during quiet hours
        </label>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="text-sm">
            <span className="text-muted">Start</span>
            <select
              className="mt-1 w-full rounded-lg border border-primary/15 px-3 py-2"
              value={quiet.quiet_start_hour}
              disabled={quietBusy}
              onChange={(e) =>
                void saveQuiet({ ...quiet, quiet_start_hour: Number(e.target.value) })
              }
            >
              {Array.from({ length: 24 }, (_, hour) => (
                <option key={`start-${hour}`} value={hour}>
                  {hourLabel(hour)}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="text-muted">End</span>
            <select
              className="mt-1 w-full rounded-lg border border-primary/15 px-3 py-2"
              value={quiet.quiet_end_hour}
              disabled={quietBusy}
              onChange={(e) => void saveQuiet({ ...quiet, quiet_end_hour: Number(e.target.value) })}
            >
              {Array.from({ length: 24 }, (_, hour) => (
                <option key={`end-${hour}`} value={hour}>
                  {hourLabel(hour)}
                </option>
              ))}
            </select>
          </label>
        </div>
        {quietMessage ? <p className="mt-3 text-sm text-muted">{quietMessage}</p> : null}
      </section>
    </div>
  );
}

function BrandingTab({
  branding,
  onRefresh,
  getToken,
  orgId,
  onSaved,
}: {
  branding: BrandingPrefs;
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
  onSaved?: () => void;
}) {
  const [form, setForm] = useState(branding);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    setError(null);
    try {
      const token = await getToken();
      await settingsApi.updateBranding(token, form, orgId);
      await onRefresh();
      onSaved?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save branding.");
    }
  };

  return (
    <section className="space-y-4 rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Branding</h2>
      <p className="text-sm text-muted">
        This logo appears in the portal header and on the public track page consignees open.
      </p>
      {form.logo_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={form.logo_url}
          alt="Logo preview"
          referrerPolicy="no-referrer"
          className="h-12 w-12 rounded-lg object-cover"
        />
      ) : null}
      <Field
        label="Logo URL"
        value={form.logo_url || ""}
        onChange={(v) => setForm({ ...form, logo_url: v })}
      />
      <Field
        label="Primary color"
        value={form.primary_color}
        onChange={(v) => setForm({ ...form, primary_color: v })}
      />
      <Field
        label="Accent color"
        value={form.accent_color}
        onChange={(v) => setForm({ ...form, accent_color: v })}
      />
      <Field
        label="Tracking page message"
        value={form.tracking_page_message || ""}
        onChange={(v) => setForm({ ...form, tracking_page_message: v })}
      />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <Button size="sm" onClick={() => void save()}>
        Save branding
      </Button>
    </section>
  );
}

function TaxTab({
  tax,
  onRefresh,
  getToken,
  orgId,
}: {
  tax: SettingsOverview["tax"];
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [form, setForm] = useState(tax);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setForm(tax);
  }, [tax]);

  const save = async () => {
    const token = await getToken();
    const patch: Parameters<typeof settingsApi.updateTax>[1] = {};
    if ((form.hst_number || "") !== (tax.hst_number || "")) {
      patch.hst_number = form.hst_number || "";
    }
    if ((form.business_number || "") !== (tax.business_number || "")) {
      patch.business_number = form.business_number || "";
    }
    if (form.tax_exempt !== tax.tax_exempt) {
      patch.tax_exempt = form.tax_exempt;
    }
    if ((form.tax_region || "ON") !== (tax.tax_region || "ON")) {
      patch.tax_region = form.tax_region || "ON";
    }
    if (Object.keys(patch).length) {
      await settingsApi.updateTax(token, patch, orgId);
    }
    setSaved(true);
    await onRefresh();
    setTimeout(() => setSaved(false), 2000);
  };

  const writer = tax.tax_legal_meta;

  return (
    <section className="space-y-4 rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Tax information</h2>
      <p className="text-sm text-muted">
        Legal name on invoices is on the Business profile tab. Last save of HST, business number,
        region, or exemption wins — admin and this portal share the same fields.
      </p>
      <p className="text-sm">
        <span className="font-medium text-primary">Legal name</span>
        <span className="mt-1 block text-muted">{tax.legal_name || "—"}</span>
      </p>
      <Field
        label="HST number"
        value={form.hst_number || ""}
        onChange={(v) => setForm({ ...form, hst_number: v })}
      />
      <Field
        label="Business number"
        value={form.business_number || ""}
        onChange={(v) => setForm({ ...form, business_number: v })}
      />
      <Field
        label="Tax region"
        value={form.tax_region}
        onChange={(v) => setForm({ ...form, tax_region: v })}
      />
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={form.tax_exempt}
          onChange={(e) => setForm({ ...form, tax_exempt: e.target.checked })}
        />
        Tax exempt
      </label>
      {writer?.updated_at ? (
        <p className="text-xs text-muted">
          Last updated by {writer.updated_by || "someone"} {formatDate(writer.updated_at)}
          {writer.fields?.length ? ` · ${writer.fields.join(", ")}` : ""}
        </p>
      ) : null}
      <Button size="sm" onClick={() => void save()}>
        Save tax info
      </Button>
      {saved ? <p className="text-sm text-green-700">Saved</p> : null}
    </section>
  );
}

function DocumentsTab({
  documents,
  onRefresh,
  getToken,
  orgId,
}: {
  documents: BusinessDocument[];
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [name, setName] = useState("");
  const [docType, setDocType] = useState("hst");
  const [reference, setReference] = useState("");
  const [error, setError] = useState<string | null>(null);

  const add = async () => {
    if (!name.trim()) return;
    setError(null);
    try {
      const token = await getToken();
      await settingsApi.addDocument(
        token,
        { name: name.trim(), doc_type: docType, reference: reference.trim() || undefined },
        orgId
      );
      setName("");
      setReference("");
      await onRefresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not add document");
    }
  };

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Company documents</h2>
      <p className="mt-1 text-sm text-muted">
        HST letters, insurance, and WSIB references this company file needs. Files stay as a named
        record — PorterChain does not store the PDF here.
      </p>
      <ul className="mt-4 space-y-2 text-sm">
        {documents.length === 0 && <li className="text-muted">No documents on file yet</li>}
        {documents.map((doc) => (
          <li key={doc.id} className="flex justify-between gap-3 border-b border-primary/5 py-2">
            <span>
              <span className="font-medium">{doc.name}</span>
              <span className="ml-2 text-muted">{doc.type}</span>
              {doc.reference ? <span className="ml-2 text-muted">{doc.reference}</span> : null}
            </span>
            <button
              type="button"
              className="text-xs text-red-600"
              onClick={() =>
                void getToken().then((t) =>
                  settingsApi.deleteDocument(t, doc.id, orgId).then(onRefresh)
                )
              }
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
      <div className="mt-4 flex flex-wrap gap-2">
        <input
          className="rounded-lg border px-3 py-2 text-sm"
          placeholder="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <select
          className="rounded-lg border px-3 py-2 text-sm"
          value={docType}
          onChange={(e) => setDocType(e.target.value)}
        >
          <option value="hst">HST / tax</option>
          <option value="insurance">Insurance</option>
          <option value="wsib">WSIB</option>
          <option value="other">Other</option>
        </select>
        <input
          className="rounded-lg border px-3 py-2 text-sm"
          placeholder="Reference (optional)"
          value={reference}
          onChange={(e) => setReference(e.target.value)}
        />
        <Button size="sm" onClick={() => void add()}>
          Add document
        </Button>
      </div>
      {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
    </section>
  );
}

function PrivacyTab({ getToken, orgId }: { getToken: () => Promise<string>; orgId?: string }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [privacy, setPrivacy] = useState<PrivacyStatus | null>(null);

  const loadPrivacy = useCallback(async () => {
    const token = await getToken();
    const status = await settingsApi.privacyStatus(token, orgId);
    setPrivacy(status);
  }, [getToken, orgId]);

  useEffect(() => {
    void loadPrivacy().catch((e) => {
      setError(e instanceof Error ? e.message : "Could not load privacy status");
    });
  }, [loadPrivacy]);

  const downloadExport = async () => {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const token = await getToken();
      const payload = await settingsApi.exportPrivacy(token, orgId);
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "porterchain-company-export.json";
      a.click();
      URL.revokeObjectURL(url);
      setMessage("Export downloaded.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setBusy(false);
    }
  };

  const requestDelete = async () => {
    if (
      !window.confirm(
        "Request deletion of this company file? PorterChain will review for 30 days. Live orders and unpaid invoices are not removed automatically."
      )
    ) {
      return;
    }
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const token = await getToken();
      const result = await settingsApi.requestDeletion(token, reason || undefined, orgId);
      setMessage(`${result.message} Reference: ${result.reference}`);
      setReason("");
      await loadPrivacy();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  };

  const pending = privacy?.status === "pending";
  const erased = privacy?.status === "erased";
  const locked = pending || erased;

  return (
    <section className="space-y-4 rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Privacy</h2>
      <p className="text-sm text-muted">
        {privacy?.message ||
          "Download a copy of this company’s file, or ask PorterChain to delete it. Live orders and unpaid invoices are not wiped automatically."}
      </p>
      {pending && privacy?.delete_reference ? (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Request pending. Reference{" "}
          <span className="font-mono font-semibold">{privacy.delete_reference}</span>
          {privacy.sla_days ? ` · Review within ${privacy.sla_days} days` : ""}
        </p>
      ) : null}
      {erased ? (
        <p className="rounded-xl border border-primary/10 bg-gray-bg px-4 py-3 text-sm text-primary">
          Contact details were removed. Order numbers and invoice amounts stay on file.
        </p>
      ) : null}
      <Button size="sm" disabled={busy} onClick={() => void downloadExport()}>
        Download company export
      </Button>
      <div className="space-y-2">
        <label className="text-sm font-medium">Deletion request</label>
        <textarea
          className="w-full rounded-lg border border-primary/15 px-3 py-2 text-sm"
          rows={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Optional reason"
          disabled={locked || busy}
        />
        <Button size="sm" disabled={busy || locked} onClick={() => void requestDelete()}>
          {pending ? "Request already submitted" : erased ? "Already erased" : "Request deletion"}
        </Button>
      </div>
      {message && <p className="text-sm text-primary">{message}</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
      {(privacy?.recent_logs?.length ?? 0) > 0 ? (
        <div className="border-t border-primary/10 pt-4">
          <h3 className="text-sm font-semibold text-primary">Company activity</h3>
          <ul className="mt-2 space-y-2 text-sm">
            {privacy?.recent_logs?.slice(0, 20).map((row) => (
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
        </div>
      ) : null}
    </section>
  );
}

function Field({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  return (
    <div>
      <label className="text-sm font-medium text-primary">{label}</label>
      <input
        disabled={disabled}
        className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm disabled:bg-gray-bg"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
