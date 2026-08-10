"use client";

import Button from "@/components/ui/Button";
import { EmptyState } from "@porterchain/ui/empty-state";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { formatCents } from "@/lib/utils";
import {
  settingsApi,
  type BrandingPrefs,
  type ClaimRow,
  type NotificationPrefs,
  type SettingsOverview,
  type SupportTicket,
} from "@/lib/settings";
import { formatDate } from "@/lib/utils";
import { useCallback, useEffect, useState } from "react";

type Tab =
  | "profile"
  | "recipients"
  | "locations"
  | "billing"
  | "notifications"
  | "branding"
  | "tax"
  | "documents"
  | "contract"
  | "support"
  | "claims";

const TABS: { id: Tab; label: string }[] = [
  { id: "profile", label: "Business profile" },
  { id: "recipients", label: "Recipients" },
  { id: "locations", label: "Locations" },
  { id: "billing", label: "Billing contacts" },
  { id: "notifications", label: "Notifications" },
  { id: "branding", label: "Branding" },
  { id: "tax", label: "Tax" },
  { id: "documents", label: "Documents" },
  { id: "contract", label: "Contract" },
  { id: "support", label: "Support" },
  { id: "claims", label: "Claims" },
];

export default function SettingsClient() {
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const [tab, setTab] = useState<Tab>("profile");
  const [data, setData] = useState<SettingsOverview | null>(null);
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [claims, setClaims] = useState<ClaimRow[]>([]);
  const [recipients, setRecipients] = useState<
    Array<{ id: string; name: string; email?: string | null; phone?: string | null }>
  >([]);
  const [kb, setKb] = useState<{
    articles: Array<{ id: string; title: string; body: string }>;
    faq: Array<{ question: string; answer: string }>;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!isSignedIn) return;
    setError(null);
    try {
      const token = await getApiToken();
      const [ov, tix, cl, knowledge, recips] = await Promise.all([
        settingsApi.overview(token, orgId),
        settingsApi.supportTickets(token, orgId),
        settingsApi.claims(token, orgId),
        settingsApi.knowledgeBase(token, orgId),
        settingsApi.recipients(token, orgId),
      ]);
      setData(ov);
      setTickets(tix);
      setClaims(cl);
      setKb(knowledge);
      setRecipients(recips);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load settings");
    }
  }, [getApiToken, orgId, isSignedIn]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    void load();
  }, [isLoaded, isSignedIn, load]);

  if (!isLoaded || !data) {
    if (error) {
      return <EmptyState title="Could not load settings" hint={error} />;
    }
    return <PageSkeleton rows={5} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">Settings</h1>
        <p className="mt-1 text-sm text-muted">
          Business profile, locations, billing, tax, support, and claims
        </p>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <nav className="flex flex-wrap gap-2 border-b border-primary/10 pb-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
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
      {tab === "billing" && (
        <BillingContactsTab
          contacts={data.billing_contacts}
          onRefresh={load}
          getToken={getApiToken}
          orgId={orgId}
        />
      )}
      {tab === "notifications" && (
        <NotificationsTab
          prefs={data.notifications}
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
        />
      )}
      {tab === "tax" && (
        <TaxTab tax={data.tax} onRefresh={load} getToken={getApiToken} orgId={orgId} />
      )}
      {tab === "documents" && (
        <DocumentsTab docs={data.documents} onRefresh={load} getToken={getApiToken} orgId={orgId} />
      )}
      {tab === "contract" && <ContractTab contract={data.contract} />}
      {tab === "support" && (
        <SupportTab
          tickets={tickets}
          kb={kb}
          onRefresh={load}
          getToken={getApiToken}
          orgId={orgId}
        />
      )}
      {tab === "claims" && (
        <ClaimsTab claims={claims} onRefresh={load} getToken={getApiToken} orgId={orgId} />
      )}
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
      <h2 className="font-semibold text-primary">Recipients</h2>
      <p className="mt-1 text-sm text-muted">
        Saved delivery contacts for booking and bulk import.
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

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = await getToken();
    await settingsApi.updateProfile(
      token,
      {
        company_name: form.company_name,
        legal_name: form.legal_name || undefined,
        phone: form.phone || undefined,
      },
      orgId
    );
    setSaved(true);
    await onRefresh();
    setTimeout(() => setSaved(false), 2000);
  };

  return (
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
      <Field label="Email" value={form.email} onChange={() => {}} disabled />
      <Field
        label="Phone"
        value={form.phone || ""}
        onChange={(v) => setForm({ ...form, phone: v })}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <p className="text-sm font-medium">Payment terms</p>
          <p className="mt-1 text-sm text-muted">{form.payment_terms.replace("_", " ")}</p>
        </div>
        <div>
          <p className="text-sm font-medium">Billing cycle</p>
          <p className="mt-1 text-sm text-muted">{form.billing_cycle}</p>
        </div>
      </div>
      <Button type="submit">Save profile</Button>
      {saved && <p className="text-sm text-green-700">Saved</p>}
    </form>
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
  const [pickupAddr, setPickupAddr] = useState("");
  const [whName, setWhName] = useState("");
  const [whAddr, setWhAddr] = useState("");

  const addPickup = async () => {
    const token = await getToken();
    await settingsApi.addPickup(
      token,
      { label: pickupLabel, formatted: pickupAddr, is_default: false },
      orgId
    );
    setPickupLabel("");
    setPickupAddr("");
    await onRefresh();
  };

  const addWarehouse = async () => {
    const token = await getToken();
    await settingsApi.addWarehouse(token, { name: whName, formatted: whAddr }, orgId);
    setWhName("");
    setWhAddr("");
    await onRefresh();
  };

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Pickup locations</h2>
        <ul className="mt-4 space-y-2 text-sm">
          {data.pickup_locations.map((p) => (
            <li key={p.id} className="flex justify-between gap-2">
              <span>
                <span className="font-medium">{p.label}</span>
                <span className="block text-muted">{p.formatted}</span>
              </span>
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
            </li>
          ))}
        </ul>
        <div className="mt-4 space-y-2">
          <input
            className="w-full rounded-lg border px-3 py-2 text-sm"
            placeholder="Label"
            value={pickupLabel}
            onChange={(e) => setPickupLabel(e.target.value)}
          />
          <input
            className="w-full rounded-lg border px-3 py-2 text-sm"
            placeholder="Address"
            value={pickupAddr}
            onChange={(e) => setPickupAddr(e.target.value)}
          />
          <Button size="sm" onClick={() => void addPickup()}>
            Add pickup
          </Button>
        </div>
      </section>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Warehouses</h2>
        <ul className="mt-4 space-y-2 text-sm">
          {data.warehouses.map((w) => (
            <li key={w.id} className="flex justify-between gap-2">
              <span>
                <span className="font-medium">{w.name}</span>
                <span className="block text-muted">{w.formatted}</span>
              </span>
              <button
                type="button"
                className="text-xs text-red-600"
                onClick={() =>
                  void getToken().then((t) =>
                    settingsApi.deleteWarehouse(t, w.id, orgId).then(onRefresh)
                  )
                }
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
        <div className="mt-4 space-y-2">
          <input
            className="w-full rounded-lg border px-3 py-2 text-sm"
            placeholder="Warehouse name"
            value={whName}
            onChange={(e) => setWhName(e.target.value)}
          />
          <input
            className="w-full rounded-lg border px-3 py-2 text-sm"
            placeholder="Address"
            value={whAddr}
            onChange={(e) => setWhAddr(e.target.value)}
          />
          <Button size="sm" onClick={() => void addWarehouse()}>
            Add warehouse
          </Button>
        </div>
      </section>
    </div>
  );
}

function BillingContactsTab({
  contacts,
  onRefresh,
  getToken,
  orgId,
}: {
  contacts: SettingsOverview["billing_contacts"];
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");

  const add = async () => {
    const token = await getToken();
    await settingsApi.addBillingContact(token, { name, email }, orgId);
    setName("");
    setEmail("");
    await onRefresh();
  };

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Billing contacts</h2>
      <ul className="mt-4 space-y-2 text-sm">
        {contacts.map((c) => (
          <li key={c.id} className="flex justify-between">
            <span>
              {c.name} · {c.email}
            </span>
            <button
              type="button"
              className="text-xs text-red-600"
              onClick={() =>
                void getToken().then((t) =>
                  settingsApi.deleteBillingContact(t, c.id, orgId).then(onRefresh)
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
        <Button size="sm" onClick={() => void add()}>
          Add contact
        </Button>
      </div>
    </section>
  );
}

function NotificationsTab({
  prefs,
  onRefresh,
  getToken,
  orgId,
}: {
  prefs: NotificationPrefs;
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
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
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Notification preferences</h2>
      <p className="mt-1 text-xs text-muted">
        Changes apply to PorterChain delivery (email and in-app). SMS stays off until enabled.
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
  );
}

function BrandingTab({
  branding,
  onRefresh,
  getToken,
  orgId,
}: {
  branding: BrandingPrefs;
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [form, setForm] = useState(branding);

  const save = async () => {
    const token = await getToken();
    await settingsApi.updateBranding(token, form, orgId);
    await onRefresh();
  };

  return (
    <section className="space-y-4 rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Branding</h2>
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

  const save = async () => {
    const token = await getToken();
    await settingsApi.updateTax(
      token,
      {
        hst_number: form.hst_number || undefined,
        business_number: form.business_number || undefined,
        legal_name: form.legal_name || undefined,
        tax_exempt: form.tax_exempt,
        tax_region: form.tax_region,
      },
      orgId
    );
    await onRefresh();
  };

  return (
    <section className="space-y-4 rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Tax information</h2>
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
        label="Legal name"
        value={form.legal_name || ""}
        onChange={(v) => setForm({ ...form, legal_name: v })}
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
      <Button size="sm" onClick={() => void save()}>
        Save tax info
      </Button>
    </section>
  );
}

function DocumentsTab({
  docs,
  onRefresh,
  getToken,
  orgId,
}: {
  docs: SettingsOverview["documents"];
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [name, setName] = useState("");
  const [docType, setDocType] = useState("insurance");

  const add = async () => {
    const token = await getToken();
    await settingsApi.addDocument(token, { name, doc_type: docType }, orgId);
    setName("");
    await onRefresh();
  };

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Business documents</h2>
      <ul className="mt-4 space-y-2 text-sm">
        {docs.map((d) => (
          <li key={d.id} className="flex justify-between">
            <span>
              {d.name} <span className="text-muted">({d.type})</span>
            </span>
            <button
              type="button"
              className="text-xs text-red-600"
              onClick={() =>
                void getToken().then((t) =>
                  settingsApi.deleteDocument(t, d.id, orgId).then(onRefresh)
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
          placeholder="Document name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <select
          className="rounded-lg border px-3 py-2 text-sm"
          value={docType}
          onChange={(e) => setDocType(e.target.value)}
        >
          <option value="insurance">Insurance</option>
          <option value="license">License</option>
          <option value="contract">Contract</option>
          <option value="other">Other</option>
        </select>
        <Button size="sm" onClick={() => void add()}>
          Register document
        </Button>
      </div>
    </section>
  );
}

function ContractTab({ contract }: { contract: SettingsOverview["contract"] }) {
  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Contract summary</h2>
      {contract.has_contract ? (
        <dl className="mt-4 space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-muted">Contract</dt>
            <dd>{contract.contract_name}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-muted">Minimum monthly</dt>
            <dd>{formatCents(contract.minimum_monthly_commitment_cents)}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-muted">Effective from</dt>
            <dd>{contract.effective_from || "—"}</dd>
          </div>
        </dl>
      ) : (
        <p className="mt-4 text-sm text-muted">
          No active contract on file. Standard NET billing applies.
        </p>
      )}
    </section>
  );
}

function SupportTab({
  tickets,
  kb,
  onRefresh,
  getToken,
  orgId,
}: {
  tickets: SupportTicket[];
  kb: {
    articles: Array<{ id: string; title: string; body: string }>;
    faq: Array<{ question: string; answer: string }>;
  } | null;
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");

  const create = async () => {
    const token = await getToken();
    await settingsApi.createTicket(token, { subject, description }, orgId);
    setSubject("");
    setDescription("");
    await onRefresh();
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Open a support ticket</h2>
        <div className="mt-4 space-y-2">
          <input
            className="w-full rounded-lg border px-3 py-2 text-sm"
            placeholder="Subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
          <textarea
            className="w-full rounded-lg border px-3 py-2 text-sm"
            rows={3}
            placeholder="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <Button size="sm" onClick={() => void create()}>
            Submit ticket
          </Button>
        </div>
      </section>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Ticket history</h2>
        <ul className="mt-4 space-y-2 text-sm">
          {tickets.length === 0 && <li className="text-muted">No tickets yet</li>}
          {tickets.map((t) => (
            <li key={t.ticket_id} className="flex justify-between border-b border-primary/5 py-2">
              <span>{t.subject}</span>
              <span className="text-muted">
                {t.status} · {t.created_at ? formatDate(t.created_at) : ""}
              </span>
            </li>
          ))}
        </ul>
      </section>
      {kb && (
        <section className="rounded-2xl border border-primary/10 bg-white p-6">
          <h2 className="font-semibold text-primary">Knowledge base</h2>
          <ul className="mt-4 space-y-4 text-sm">
            {kb.articles.map((a) => (
              <li key={a.id}>
                <p className="font-medium">{a.title}</p>
                <p className="text-muted">{a.body}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function ClaimsTab({
  claims,
  onRefresh,
  getToken,
  orgId,
}: {
  claims: ClaimRow[];
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [orderId, setOrderId] = useState("");
  const [claimType, setClaimType] = useState("merchant_complaint");
  const [description, setDescription] = useState("");

  const file = async () => {
    const token = await getToken();
    await settingsApi.openClaim(
      token,
      { order_id: orderId, claim_type: claimType, description },
      orgId
    );
    setOrderId("");
    setDescription("");
    await onRefresh();
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">File a claim</h2>
        <div className="mt-4 space-y-2">
          <input
            className="w-full rounded-lg border px-3 py-2 text-sm"
            placeholder="Order ID"
            value={orderId}
            onChange={(e) => setOrderId(e.target.value)}
          />
          <select
            className="w-full rounded-lg border px-3 py-2 text-sm"
            value={claimType}
            onChange={(e) => setClaimType(e.target.value)}
          >
            <option value="merchant_complaint">Merchant complaint</option>
            <option value="damaged_parcel">Damaged parcel</option>
            <option value="lost_parcel">Lost parcel</option>
            <option value="late_delivery">Late delivery</option>
          </select>
          <textarea
            className="w-full rounded-lg border px-3 py-2 text-sm"
            rows={3}
            placeholder="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <Button size="sm" onClick={() => void file()}>
            Submit claim
          </Button>
        </div>
      </section>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Claims history</h2>
        <ul className="mt-4 space-y-2 text-sm">
          {claims.length === 0 && <li className="text-muted">No claims</li>}
          {claims.map((c) => (
            <li key={c.claim_id} className="flex justify-between border-b border-primary/5 py-2">
              <span>
                {c.claim_number} · {c.claim_type}
              </span>
              <span className="text-muted">{c.status}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
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
