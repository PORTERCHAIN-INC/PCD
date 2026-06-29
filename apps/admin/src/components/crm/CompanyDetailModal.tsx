"use client";

import { useEffect, useState } from "react";
import {
  Activity as ActivityIcon,
  Building2,
  ClipboardList,
  Contact as ContactIcon,
  FileSignature,
  FileText,
  Info,
  MapPin,
  Pencil,
  Plus,
  Rocket,
  Save,
  Send,
  Star,
  Target,
  Trash2,
  X,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import {
  crm,
  type Company,
  type Contact,
  type Contract,
  type Deal,
  type Quotation,
} from "@/lib/crm";
import { ActivityTimeline } from "@/components/crm/ActivityTimeline";
import { EntityTasks } from "@/components/crm/EntityTasks";
import { Avatar, Badge, Button, Field, Input, Select, Textarea } from "@/components/crm/primitives";
import { STAGE_LABELS, STATUS_TONE, money, shortDate, titleCase } from "@/lib/crmFormat";

const MERCHANT_STATUSES = ["lead", "prospect", "negotiating", "active_merchant", "churned"];
const NET_TERMS = ["NET_15", "NET_30", "NET_45", "NET_60", "IMMEDIATE"];
const VEHICLES = ["cargo_van", "refrigerated_van", "flatbed", "box_truck", "cargo_bike", "sedan"];

type CustomField = { key: string; value: string };
type TabId =
  "overview" | "contacts" | "deals" | "quotations" | "contracts" | "operations" | "history";

const TABS: { id: TabId; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "overview", label: "Overview", icon: Info },
  { id: "contacts", label: "Contacts", icon: ContactIcon },
  { id: "deals", label: "Deals", icon: Target },
  { id: "quotations", label: "Quotations", icon: FileText },
  { id: "contracts", label: "Contracts", icon: FileSignature },
  { id: "operations", label: "Operations", icon: ClipboardList },
  { id: "history", label: "History", icon: ActivityIcon },
];

export function CompanyDetailModal({
  company,
  onClose,
  onChanged,
}: {
  company: Company | null;
  onClose: () => void;
  onChanged?: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const [record, setRecord] = useState<Company | null>(company);
  const [tab, setTab] = useState<TabId>("overview");
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<Company>>({});
  const [customFields, setCustomFields] = useState<CustomField[]>([]);
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate modal state from the selected company prop
    setRecord(company);
    setEditing(false);
    setConfirmDelete(false);
    setToast(null);
    if (company) setTab("overview");
  }, [company]);

  useEffect(() => {
    if (!company) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && !editing && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [company, editing, onClose]);

  if (!company || !record) return null;
  const isMerchant = record.merchant_status === "active_merchant";

  async function reload() {
    if (!record) return;
    const token = await getApiToken();
    setRecord(await crm.company(token, record.id));
    onChanged?.();
  }

  function startEdit() {
    if (!record) return;
    setForm({ ...record });
    setCustomFields(
      Object.entries(record.custom_fields ?? {}).map(([key, value]) => ({
        key,
        value: String(value ?? ""),
      }))
    );
    setEditing(true);
    setTab("overview");
  }

  async function save() {
    if (!record) return;
    setSaving(true);
    try {
      const token = await getApiToken();
      const custom_fields = Object.fromEntries(
        customFields.filter((f) => f.key.trim()).map((f) => [f.key.trim(), f.value])
      );
      const updated = await crm.updateCompany(token, record.id, {
        legal_name: form.legal_name,
        operating_name: form.operating_name,
        industry: form.industry,
        business_type: form.business_type,
        website: form.website,
        email: form.email,
        phone: form.phone,
        hst_number: form.hst_number,
        business_number: form.business_number,
        address: form.address ?? {},
        service_area: form.service_area,
        preferred_vehicle: form.preferred_vehicle,
        current_logistics_provider: form.current_logistics_provider,
        estimated_deliveries_per_month: form.estimated_deliveries_per_month
          ? Number(form.estimated_deliveries_per_month)
          : null,
        estimated_monthly_revenue_cents: form.estimated_monthly_revenue_cents
          ? Number(form.estimated_monthly_revenue_cents)
          : null,
        custom_fields,
      });
      setRecord(updated);
      setEditing(false);
      onChanged?.();
    } finally {
      setSaving(false);
    }
  }

  async function changeStatus(merchant_status: string) {
    if (!record) return;
    const token = await getApiToken();
    setRecord(await crm.updateCompany(token, record.id, { merchant_status }));
    onChanged?.();
  }

  async function toggle(field: "is_pinned" | "is_favorite") {
    if (!record) return;
    const token = await getApiToken();
    setRecord(await crm.updateCompany(token, record.id, { [field]: !record[field] }));
    onChanged?.();
  }

  async function convertMerchant() {
    if (!record) return;
    setSaving(true);
    try {
      const token = await getApiToken();
      const res = await crm.convertMerchant(token, record.id);
      setToast(
        res.created
          ? `Merchant created${res.invitation_sent ? ` · invite queued to ${res.invitation_email}` : ""}.`
          : "Already a merchant."
      );
      await reload();
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!record) return;
    setSaving(true);
    try {
      const token = await getApiToken();
      await crm.deleteCompany(token, record.id);
      onChanged?.();
      onClose();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-primary/40 backdrop-blur-sm"
        onClick={editing ? undefined : onClose}
      />
      <div className="relative flex h-[88vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-primary/10 px-6 py-4">
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-secondary/10 text-secondary">
              <Building2 className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="truncate text-lg font-bold text-primary">
                  {record.operating_name || record.legal_name}
                </h2>
                <Badge tone={STATUS_TONE[record.merchant_status]}>
                  {titleCase(record.merchant_status)}
                </Badge>
                {record.is_pinned && <Badge tone="blue">Pinned</Badge>}
              </div>
              <p className="mt-0.5 text-sm text-muted">
                {record.industry ?? "—"}
                {record.service_area ? ` · ${record.service_area}` : ""}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {editing ? (
              <>
                <Button variant="outline" onClick={() => setEditing(false)} disabled={saving}>
                  Cancel
                </Button>
                <Button onClick={save} disabled={saving || !form.legal_name}>
                  <Save className="h-4 w-4" />
                  Save
                </Button>
              </>
            ) : (
              <>
                {isMerchant ? (
                  <Badge tone="green">
                    <Rocket className="h-3 w-3" /> Merchant
                  </Badge>
                ) : (
                  <Button variant="outline" onClick={convertMerchant} disabled={saving}>
                    <Rocket className="h-4 w-4" />
                    Convert
                  </Button>
                )}
                <Button variant="outline" onClick={() => toggle("is_favorite")} className="px-2">
                  <Star
                    className={cn("h-4 w-4", record.is_favorite && "fill-amber-400 text-amber-400")}
                  />
                </Button>
                <Button variant="outline" onClick={startEdit}>
                  <Pencil className="h-4 w-4" />
                  Edit
                </Button>
                <Button variant="danger" onClick={() => setConfirmDelete(true)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </>
            )}
            <button onClick={onClose} className="rounded-lg p-1.5 text-muted hover:bg-gray-bg">
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {toast && (
          <div className="border-b border-green-200 bg-green-50 px-6 py-2 text-sm text-green-700">
            {toast}
          </div>
        )}

        {/* Status control */}
        {!editing && (
          <div className="flex flex-wrap items-center gap-3 border-b border-primary/10 bg-secondary/5 px-6 py-2.5">
            <span className="text-xs font-semibold uppercase tracking-wide text-muted">
              Account status
            </span>
            <Select
              value={record.merchant_status}
              onChange={(e) => changeStatus(e.target.value)}
              disabled={saving}
              className="w-48"
            >
              {MERCHANT_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {titleCase(s)}
                </option>
              ))}
            </Select>
            {record.estimated_monthly_revenue_cents ? (
              <span className="ml-auto text-sm">
                <span className="text-muted">Est. monthly value </span>
                <span className="font-bold text-secondary">
                  {money(record.estimated_monthly_revenue_cents)}
                </span>
              </span>
            ) : null}
          </div>
        )}

        {/* Tabs */}
        {!editing && (
          <div className="flex gap-1 overflow-x-auto border-b border-primary/10 px-4 py-2">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={cn(
                  "flex shrink-0 items-center gap-2 rounded-xl px-3 py-1.5 text-sm font-medium transition-colors",
                  tab === id ? "bg-secondary text-white" : "text-primary/70 hover:bg-gray-bg"
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </div>
        )}

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {editing ? (
            <CompanyEditForm
              form={form}
              setForm={setForm}
              customFields={customFields}
              setCustomFields={setCustomFields}
            />
          ) : (
            <>
              {tab === "overview" && <Overview company={record} />}
              {tab === "contacts" && <Contacts companyId={record.id} />}
              {tab === "deals" && <Deals companyId={record.id} />}
              {tab === "quotations" && <Quotations companyId={record.id} onChanged={onChanged} />}
              {tab === "contracts" && <Contracts companyId={record.id} onChanged={onChanged} />}
              {tab === "operations" && (
                <EntityTasks entityType="company" entityId={record.id} companyId={record.id} />
              )}
              {tab === "history" && <ActivityTimeline entityType="company" entityId={record.id} />}
            </>
          )}
        </div>
      </div>

      {confirmDelete && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-primary/40" onClick={() => setConfirmDelete(false)} />
          <div className="relative w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-base font-semibold text-primary">Delete company?</h3>
            <p className="mt-1 text-sm text-muted">
              This permanently removes{" "}
              <span className="font-medium text-primary">{record.legal_name}</span> and its
              contacts. This cannot be undone.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setConfirmDelete(false)} disabled={saving}>
                Cancel
              </Button>
              <Button variant="danger" onClick={remove} disabled={saving}>
                <Trash2 className="h-4 w-4" />
                Delete
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="text-sm text-primary">{value || "—"}</dd>
    </div>
  );
}

function Overview({ company }: { company: Company }) {
  const a = (company.address as Record<string, string>) ?? {};
  const addressParts = [a.street, a.city, a.province, a.postal_code, a.country].filter(Boolean);
  return (
    <div className="space-y-6">
      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">Company</h3>
        <dl className="grid grid-cols-2 gap-4 md:grid-cols-3">
          <Detail label="Legal name" value={company.legal_name} />
          <Detail label="Operating name" value={company.operating_name} />
          <Detail label="Industry" value={company.industry} />
          <Detail label="Business type" value={company.business_type} />
          <Detail label="Website" value={company.website} />
          <Detail label="Email" value={company.email} />
          <Detail label="Phone" value={company.phone} />
          <Detail label="HST number" value={company.hst_number} />
          <Detail label="Business number" value={company.business_number} />
        </dl>
      </section>
      <section>
        <h3 className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted">
          <MapPin className="h-3.5 w-3.5" /> Address & logistics
        </h3>
        <dl className="grid grid-cols-2 gap-4 md:grid-cols-3">
          <Detail label="Address" value={addressParts.length ? addressParts.join(", ") : null} />
          <Detail label="Service area" value={company.service_area} />
          <Detail label="Current provider" value={company.current_logistics_provider} />
          <Detail
            label="Deliveries / month"
            value={company.estimated_deliveries_per_month?.toString()}
          />
          <Detail label="Monthly value" value={money(company.estimated_monthly_revenue_cents)} />
          <Detail label="Preferred vehicle" value={titleCase(company.preferred_vehicle ?? "")} />
        </dl>
      </section>
      {company.custom_fields && Object.keys(company.custom_fields).length > 0 && (
        <section>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">
            Custom fields
          </h3>
          <dl className="grid grid-cols-2 gap-4 md:grid-cols-3">
            {Object.entries(company.custom_fields).map(([k, v]) => (
              <Detail key={k} label={titleCase(k)} value={v == null ? null : String(v)} />
            ))}
          </dl>
        </section>
      )}
    </div>
  );
}

function Contacts({ companyId }: { companyId: string }) {
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const { data } = useApiData(
    (t) => crm.contacts(t, { company_id: companyId }),
    [companyId, version]
  );
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState<Partial<Contact>>({ first_name: "" });
  const [busy, setBusy] = useState(false);

  async function add() {
    if (!form.first_name) return;
    setBusy(true);
    try {
      const token = await getApiToken();
      await crm.createContact(token, { ...form, company_id: companyId });
      setForm({ first_name: "" });
      setAdding(false);
      setVersion((v) => v + 1);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Button variant={adding ? "outline" : "primary"} onClick={() => setAdding(!adding)}>
          <Plus className="h-4 w-4" />
          {adding ? "Cancel" : "Add contact"}
        </Button>
      </div>
      {adding && (
        <div className="grid grid-cols-2 gap-3 rounded-xl border border-primary/10 bg-gray-bg/30 p-4">
          <Field label="First name *">
            <Input
              value={form.first_name ?? ""}
              onChange={(e) => setForm({ ...form, first_name: e.target.value })}
            />
          </Field>
          <Field label="Last name">
            <Input
              value={form.last_name ?? ""}
              onChange={(e) => setForm({ ...form, last_name: e.target.value })}
            />
          </Field>
          <Field label="Designation">
            <Input
              value={form.designation ?? ""}
              onChange={(e) => setForm({ ...form, designation: e.target.value })}
            />
          </Field>
          <Field label="Email">
            <Input
              value={form.email ?? ""}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </Field>
          <Field label="Phone">
            <Input
              value={form.phone ?? ""}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
            />
          </Field>
          <div className="flex items-end">
            <Button onClick={add} disabled={busy || !form.first_name}>
              Save contact
            </Button>
          </div>
        </div>
      )}
      <div className="space-y-2">
        {(data ?? []).map((c) => (
          <div
            key={c.id}
            className="flex items-center gap-3 rounded-xl border border-primary/10 p-2.5"
          >
            <Avatar name={`${c.first_name} ${c.last_name ?? ""}`} />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-primary">
                {c.first_name} {c.last_name} {c.is_primary && <Badge tone="blue">Primary</Badge>}
              </p>
              <p className="truncate text-xs text-muted">
                {c.designation ?? "—"} · {c.email ?? c.phone ?? ""}
              </p>
            </div>
          </div>
        ))}
        {(!data || data.length === 0) && (
          <p className="py-6 text-center text-sm text-muted">No contacts yet.</p>
        )}
      </div>
    </div>
  );
}

function Deals({ companyId }: { companyId: string }) {
  const { data } = useApiData((t) => crm.deals(t, { company_id: companyId }), [companyId]);
  return (
    <div className="space-y-2">
      {(data ?? []).map((d: Deal) => (
        <div
          key={d.id}
          className="flex items-center justify-between rounded-xl border border-primary/10 p-3"
        >
          <div>
            <p className="text-sm font-semibold text-primary">{d.name}</p>
            <p className="text-xs text-muted">
              {money(d.expected_revenue_cents)} · {d.probability}% win
            </p>
          </div>
          <Badge tone={STATUS_TONE[d.stage]}>{STAGE_LABELS[d.stage] ?? titleCase(d.stage)}</Badge>
        </div>
      ))}
      {(!data || data.length === 0) && (
        <p className="py-6 text-center text-sm text-muted">No deals yet.</p>
      )}
    </div>
  );
}

type DraftLine = { label: string; quantity: number; unit_price_cents: number };

function Quotations({ companyId, onChanged }: { companyId: string; onChanged?: () => void }) {
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const { data } = useApiData(
    (t) => crm.quotations(t, { company_id: companyId }),
    [companyId, version]
  );
  const [creating, setCreating] = useState(false);
  const [lines, setLines] = useState<DraftLine[]>([
    { label: "", quantity: 1, unit_price_cents: 0 },
  ]);
  const [taxCents, setTaxCents] = useState(0);
  const [busy, setBusy] = useState(false);
  const subtotal = lines.reduce((s, l) => s + l.quantity * l.unit_price_cents, 0);

  async function create() {
    const valid = lines.filter((l) => l.label.trim());
    if (!valid.length) return;
    setBusy(true);
    try {
      const token = await getApiToken();
      await crm.createQuotation(token, {
        company_id: companyId,
        line_items: valid,
        tax_cents: Number(taxCents) || 0,
      });
      setCreating(false);
      setLines([{ label: "", quantity: 1, unit_price_cents: 0 }]);
      setTaxCents(0);
      setVersion((v) => v + 1);
      onChanged?.();
    } finally {
      setBusy(false);
    }
  }

  async function setStatus(q: Quotation, status: string) {
    const token = await getApiToken();
    await crm.setQuotationStatus(token, q.id, status);
    setVersion((v) => v + 1);
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Button variant={creating ? "outline" : "primary"} onClick={() => setCreating(!creating)}>
          <Plus className="h-4 w-4" />
          {creating ? "Cancel" : "New quotation"}
        </Button>
      </div>
      {creating && (
        <div className="space-y-2 rounded-xl border border-primary/10 bg-gray-bg/30 p-4">
          {lines.map((line, i) => (
            <div key={i} className="flex items-center gap-2">
              <Input
                placeholder="Description"
                value={line.label}
                onChange={(e) =>
                  setLines(lines.map((l, j) => (j === i ? { ...l, label: e.target.value } : l)))
                }
              />
              <Input
                type="number"
                className="w-20"
                value={line.quantity}
                onChange={(e) =>
                  setLines(
                    lines.map((l, j) => (j === i ? { ...l, quantity: Number(e.target.value) } : l))
                  )
                }
              />
              <Input
                type="number"
                className="w-28"
                placeholder="Unit ¢"
                value={line.unit_price_cents}
                onChange={(e) =>
                  setLines(
                    lines.map((l, j) =>
                      j === i ? { ...l, unit_price_cents: Number(e.target.value) } : l
                    )
                  )
                }
              />
              <button
                onClick={() => setLines(lines.filter((_, j) => j !== i))}
                className="rounded-lg p-2 text-muted hover:bg-white"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
          <div className="flex items-center justify-between">
            <Button
              variant="ghost"
              onClick={() => setLines([...lines, { label: "", quantity: 1, unit_price_cents: 0 }])}
            >
              <Plus className="h-4 w-4" /> Add line
            </Button>
            <div className="flex items-center gap-3">
              <Field label="Tax ¢">
                <Input
                  type="number"
                  className="w-24"
                  value={taxCents}
                  onChange={(e) => setTaxCents(Number(e.target.value))}
                />
              </Field>
              <div className="text-right">
                <p className="text-xs text-muted">Total</p>
                <p className="font-bold text-primary">{money(subtotal + Number(taxCents || 0))}</p>
              </div>
              <Button onClick={create} disabled={busy}>
                Create
              </Button>
            </div>
          </div>
        </div>
      )}
      <div className="space-y-2">
        {(data ?? []).map((q) => (
          <div
            key={q.id}
            className="flex items-center justify-between rounded-xl border border-primary/10 p-3"
          >
            <div>
              <p className="text-sm font-semibold text-primary">
                {q.quote_number} <span className="text-xs text-muted">v{q.version}</span>
              </p>
              <p className="text-xs text-muted">{money(q.total_cents)}</p>
            </div>
            <div className="flex items-center gap-2">
              <Badge tone={STATUS_TONE[q.status]}>{titleCase(q.status)}</Badge>
              {q.status === "draft" && (
                <Button
                  variant="outline"
                  onClick={() => setStatus(q, "sent")}
                  className="px-2 py-1 text-xs"
                >
                  <Send className="h-3.5 w-3.5" /> Send
                </Button>
              )}
            </div>
          </div>
        ))}
        {(!data || data.length === 0) && !creating && (
          <p className="py-6 text-center text-sm text-muted">No quotations yet.</p>
        )}
      </div>
    </div>
  );
}

function Contracts({ companyId, onChanged }: { companyId: string; onChanged?: () => void }) {
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const { data } = useApiData(
    (t) => crm.contracts(t, { company_id: companyId }),
    [companyId, version]
  );
  const [netTerms, setNetTerms] = useState("NET_30");
  const [value, setValue] = useState(0);
  const [busy, setBusy] = useState(false);

  async function create() {
    setBusy(true);
    try {
      const token = await getApiToken();
      await crm.createContract(token, {
        company_id: companyId,
        net_terms: netTerms,
        value_cents: Number(value) || 0,
      });
      setValue(0);
      setVersion((v) => v + 1);
      onChanged?.();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-primary/10 bg-gray-bg/30 p-4">
        <Field label="Net terms">
          <Select value={netTerms} onChange={(e) => setNetTerms(e.target.value)} className="w-36">
            {NET_TERMS.map((t) => (
              <option key={t} value={t}>
                {titleCase(t)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Annual value ¢">
          <Input
            type="number"
            className="w-32"
            value={value}
            onChange={(e) => setValue(Number(e.target.value))}
          />
        </Field>
        <Button onClick={create} disabled={busy}>
          <Plus className="h-4 w-4" /> Draft contract
        </Button>
      </div>
      <div className="space-y-2">
        {(data ?? []).map((c: Contract) => (
          <div
            key={c.id}
            className="flex items-center justify-between rounded-xl border border-primary/10 p-3"
          >
            <div>
              <p className="text-sm font-semibold text-primary">{c.contract_number}</p>
              <p className="text-xs text-muted">
                {titleCase(c.net_terms)} · {money(c.value_cents)} · expires{" "}
                {shortDate(c.expiry_date)}
              </p>
            </div>
            <Badge tone={STATUS_TONE[c.status]}>{titleCase(c.status)}</Badge>
          </div>
        ))}
        {(!data || data.length === 0) && (
          <p className="py-6 text-center text-sm text-muted">No contracts yet.</p>
        )}
      </div>
    </div>
  );
}

function CompanyEditForm({
  form,
  setForm,
  customFields,
  setCustomFields,
}: {
  form: Partial<Company>;
  setForm: (f: Partial<Company>) => void;
  customFields: CustomField[];
  setCustomFields: (f: CustomField[]) => void;
}) {
  const addr = (form.address as Record<string, string>) ?? {};
  const setAddr = (patch: Record<string, string>) =>
    setForm({ ...form, address: { ...addr, ...patch } });

  return (
    <div className="space-y-6">
      <section className="grid grid-cols-2 gap-4">
        <Field label="Legal name *">
          <Input
            value={form.legal_name ?? ""}
            onChange={(e) => setForm({ ...form, legal_name: e.target.value })}
          />
        </Field>
        <Field label="Operating name">
          <Input
            value={form.operating_name ?? ""}
            onChange={(e) => setForm({ ...form, operating_name: e.target.value })}
          />
        </Field>
        <Field label="Industry">
          <Input
            value={form.industry ?? ""}
            onChange={(e) => setForm({ ...form, industry: e.target.value })}
          />
        </Field>
        <Field label="Business type">
          <Input
            value={form.business_type ?? ""}
            onChange={(e) => setForm({ ...form, business_type: e.target.value })}
          />
        </Field>
        <Field label="Website">
          <Input
            value={form.website ?? ""}
            onChange={(e) => setForm({ ...form, website: e.target.value })}
          />
        </Field>
        <Field label="Email">
          <Input
            value={form.email ?? ""}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        </Field>
        <Field label="Phone">
          <Input
            value={form.phone ?? ""}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
          />
        </Field>
        <Field label="HST number">
          <Input
            value={form.hst_number ?? ""}
            onChange={(e) => setForm({ ...form, hst_number: e.target.value })}
          />
        </Field>
        <Field label="Business number">
          <Input
            value={form.business_number ?? ""}
            onChange={(e) => setForm({ ...form, business_number: e.target.value })}
          />
        </Field>
      </section>

      <section>
        <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted">
          <MapPin className="h-3.5 w-3.5" /> Address
        </p>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Street" className="col-span-2">
            <Input
              value={addr.street ?? ""}
              onChange={(e) => setAddr({ street: e.target.value })}
            />
          </Field>
          <Field label="City">
            <Input value={addr.city ?? ""} onChange={(e) => setAddr({ city: e.target.value })} />
          </Field>
          <Field label="Province">
            <Input
              value={addr.province ?? ""}
              onChange={(e) => setAddr({ province: e.target.value })}
            />
          </Field>
          <Field label="Postal code">
            <Input
              value={addr.postal_code ?? ""}
              onChange={(e) => setAddr({ postal_code: e.target.value })}
            />
          </Field>
          <Field label="Country">
            <Input
              value={addr.country ?? ""}
              onChange={(e) => setAddr({ country: e.target.value })}
            />
          </Field>
        </div>
      </section>

      <section className="grid grid-cols-2 gap-4">
        <Field label="Service area">
          <Input
            value={form.service_area ?? ""}
            onChange={(e) => setForm({ ...form, service_area: e.target.value })}
          />
        </Field>
        <Field label="Preferred vehicle">
          <Select
            value={form.preferred_vehicle ?? ""}
            onChange={(e) => setForm({ ...form, preferred_vehicle: e.target.value })}
          >
            <option value="">—</option>
            {VEHICLES.map((v) => (
              <option key={v} value={v}>
                {titleCase(v)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Deliveries / month">
          <Input
            type="number"
            value={(form.estimated_deliveries_per_month as number) ?? ""}
            onChange={(e) =>
              setForm({ ...form, estimated_deliveries_per_month: Number(e.target.value) })
            }
          />
        </Field>
        <Field label="Est. monthly value (cents)">
          <Input
            type="number"
            value={(form.estimated_monthly_revenue_cents as number) ?? ""}
            onChange={(e) =>
              setForm({ ...form, estimated_monthly_revenue_cents: Number(e.target.value) })
            }
          />
        </Field>
        <Field label="Current provider" className="col-span-2">
          <Input
            value={form.current_logistics_provider ?? ""}
            onChange={(e) => setForm({ ...form, current_logistics_provider: e.target.value })}
          />
        </Field>
      </section>

      <section>
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">Custom fields</p>
          <Button
            variant="ghost"
            className="text-xs"
            onClick={() => setCustomFields([...customFields, { key: "", value: "" }])}
          >
            <Plus className="h-4 w-4" />
            Add field
          </Button>
        </div>
        <div className="space-y-2">
          {customFields.map((f, i) => (
            <div key={i} className="flex items-center gap-2">
              <Input
                placeholder="Field name"
                value={f.key}
                onChange={(e) =>
                  setCustomFields(
                    customFields.map((c, j) => (j === i ? { ...c, key: e.target.value } : c))
                  )
                }
              />
              <Input
                placeholder="Value"
                value={f.value}
                onChange={(e) =>
                  setCustomFields(
                    customFields.map((c, j) => (j === i ? { ...c, value: e.target.value } : c))
                  )
                }
              />
              <button
                onClick={() => setCustomFields(customFields.filter((_, j) => j !== i))}
                className="rounded-lg p-2 text-muted hover:bg-gray-bg"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
          {customFields.length === 0 && (
            <p className="text-xs text-muted">Add any extra attribute for this account.</p>
          )}
        </div>
      </section>
    </div>
  );
}
