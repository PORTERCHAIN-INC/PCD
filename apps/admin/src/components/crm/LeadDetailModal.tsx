"use client";

import { useEffect, useState } from "react";
import {
  Activity as ActivityIcon,
  ArrowRight,
  CalendarDays,
  ClipboardList,
  Contact as ContactIcon,
  FileSignature,
  FileText,
  Info,
  MapPin,
  Pencil,
  Plus,
  Save,
  Send,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { crm, type Contact, type Contract, type Lead, type Quotation } from "@/lib/crm";
import { ActivityTimeline } from "@/components/crm/ActivityTimeline";
import { EntityTasks } from "@/components/crm/EntityTasks";
import { MiniCalendar } from "@/components/crm/MiniCalendar";
import { Avatar, Badge, Button, Field, Input, Select, Textarea } from "@/components/crm/primitives";
import { STAGE_LABELS, STATUS_TONE, money, shortDate, titleCase } from "@/lib/crmFormat";

const DEAL_STAGES = [
  "prospecting",
  "qualified",
  "meeting_scheduled",
  "quote_sent",
  "negotiation",
  "contract_review",
  "won",
  "lost",
  "hold",
];

const LEAD_STATUSES = ["new", "contacted", "qualified", "nurturing", "unqualified", "converted"];
const LEAD_PRIORITIES = ["low", "medium", "high", "urgent"];
const LEAD_SOURCES = [
  "website",
  "for_business",
  "referral",
  "csv_import",
  "vendor_import",
  "cold_outreach",
  "event",
];
const LEAD_VEHICLES = [
  "cargo_van",
  "refrigerated_van",
  "flatbed",
  "box_truck",
  "cargo_bike",
  "sedan",
];

type CustomField = { key: string; value: string };

type TabId =
  "overview" | "contacts" | "followups" | "activity" | "quotations" | "contracts" | "calendar";

const TABS: { id: TabId; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "overview", label: "Overview", icon: Info },
  { id: "contacts", label: "Contacts", icon: ContactIcon },
  { id: "followups", label: "Follow-ups", icon: ClipboardList },
  { id: "activity", label: "Activity", icon: ActivityIcon },
  { id: "quotations", label: "Quotations", icon: FileText },
  { id: "contracts", label: "Contracts", icon: FileSignature },
  { id: "calendar", label: "Calendar", icon: CalendarDays },
];

export function LeadDetailModal({
  lead,
  onClose,
  onConvert,
  busy,
  onChanged,
}: {
  lead: Lead | null;
  onClose: () => void;
  onConvert: (lead: Lead) => void;
  busy: boolean;
  onChanged?: () => void;
}) {
  const [tab, setTab] = useState<TabId>("overview");
  const [record, setRecord] = useState<Lead | null>(lead);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<Lead>>({});
  const [customFields, setCustomFields] = useState<CustomField[]>([]);
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const { getApiToken } = useAdminAuth();

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate modal state from the selected lead prop
    setRecord(lead);
    setEditing(false);
    setConfirmDelete(false);
    if (lead) setTab("overview");
  }, [lead]);

  useEffect(() => {
    if (!lead) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [lead, onClose]);

  if (!lead || !record) return null;
  const converted = record.status === "converted";

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
      const payload: Partial<Lead> = {
        company_name: form.company_name,
        industry: form.industry,
        business_type: form.business_type,
        website: form.website,
        primary_contact_name: form.primary_contact_name,
        email: form.email,
        phone: form.phone,
        address: form.address ?? {},
        service_area: form.service_area,
        preferred_vehicle: form.preferred_vehicle,
        current_logistics_provider: form.current_logistics_provider,
        estimated_deliveries_per_month: form.estimated_deliveries_per_month
          ? Number(form.estimated_deliveries_per_month)
          : null,
        estimated_revenue_cents: form.estimated_revenue_cents
          ? Number(form.estimated_revenue_cents)
          : null,
        source: form.source,
        status: form.status,
        priority: form.priority,
        expected_close_date: form.expected_close_date || null,
        internal_notes: form.internal_notes,
        custom_fields,
      };
      const updated = await crm.updateLead(token, record.id, payload);
      setRecord(updated);
      setEditing(false);
      onChanged?.();
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!record) return;
    setSaving(true);
    try {
      const token = await getApiToken();
      await crm.deleteLead(token, record.id);
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
      <div className="relative flex h-[86vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-primary/10 px-6 py-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="truncate text-lg font-bold text-primary">{record.company_name}</h2>
              <Badge tone={STATUS_TONE[record.status]}>{titleCase(record.status)}</Badge>
              <Badge tone={STATUS_TONE[record.priority]}>{titleCase(record.priority)}</Badge>
              <Badge
                tone={
                  record.lead_score >= 70 ? "green" : record.lead_score >= 40 ? "amber" : "slate"
                }
              >
                <Sparkles className="h-3 w-3" />
                {record.lead_score}
              </Badge>
            </div>
            <p className="mt-0.5 text-sm text-muted">
              {record.industry ?? "—"} · {titleCase(record.source)}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {editing ? (
              <>
                <Button variant="outline" onClick={() => setEditing(false)} disabled={saving}>
                  Cancel
                </Button>
                <Button onClick={save} disabled={saving || !form.company_name}>
                  <Save className="h-4 w-4" />
                  Save
                </Button>
              </>
            ) : (
              <>
                {!converted && (
                  <Button variant="outline" onClick={() => onConvert(record)} disabled={busy}>
                    Convert <ArrowRight className="h-4 w-4" />
                  </Button>
                )}
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

        {/* Linked deal stage control */}
        {record.deal_id && !editing && (
          <DealStageBar dealId={record.deal_id} onChanged={onChanged} />
        )}

        {/* Tabs (hidden while editing) */}
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
            <LeadEditForm
              form={form}
              setForm={setForm}
              customFields={customFields}
              setCustomFields={setCustomFields}
            />
          ) : (
            <>
              {tab === "overview" && <Overview lead={record} />}
              {tab === "contacts" && (
                <LeadContacts lead={record} onConvert={() => onConvert(record)} busy={busy} />
              )}
              {tab === "followups" && (
                <EntityTasks
                  entityType="lead"
                  entityId={record.id}
                  companyId={record.company_id}
                  dealId={record.deal_id}
                />
              )}
              {tab === "activity" && <ActivityTimeline entityType="lead" entityId={record.id} />}
              {tab === "quotations" && (
                <LeadQuotations lead={record} onConvert={() => onConvert(record)} busy={busy} />
              )}
              {tab === "contracts" && (
                <LeadContracts lead={record} onConvert={() => onConvert(record)} busy={busy} />
              )}
              {tab === "calendar" && <LeadCalendar leadId={record.id} />}
            </>
          )}
        </div>
      </div>

      {/* Delete confirmation */}
      {confirmDelete && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-primary/40" onClick={() => setConfirmDelete(false)} />
          <div className="relative w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-base font-semibold text-primary">Delete lead?</h3>
            <p className="mt-1 text-sm text-muted">
              This permanently removes{" "}
              <span className="font-medium text-primary">{record.company_name}</span> and its
              tasks/activities are no longer linked. This cannot be undone.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setConfirmDelete(false)} disabled={saving}>
                Cancel
              </Button>
              <Button variant="danger" onClick={remove} disabled={saving}>
                <Trash2 className="h-4 w-4" />
                Delete lead
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function LeadEditForm({
  form,
  setForm,
  customFields,
  setCustomFields,
}: {
  form: Partial<Lead>;
  setForm: (f: Partial<Lead>) => void;
  customFields: CustomField[];
  setCustomFields: (f: CustomField[]) => void;
}) {
  const addr = (form.address as Record<string, string>) ?? {};
  const setAddr = (patch: Record<string, string>) =>
    setForm({ ...form, address: { ...addr, ...patch } });

  return (
    <div className="space-y-6">
      <section className="grid grid-cols-2 gap-4">
        <Field label="Company name *" className="col-span-2">
          <Input
            value={form.company_name ?? ""}
            onChange={(e) => setForm({ ...form, company_name: e.target.value })}
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
        <Field label="Primary contact">
          <Input
            value={form.primary_contact_name ?? ""}
            onChange={(e) => setForm({ ...form, primary_contact_name: e.target.value })}
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

      <section>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
          Logistics profile
        </p>
        <div className="grid grid-cols-2 gap-4">
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
              {LEAD_VEHICLES.map((v) => (
                <option key={v} value={v}>
                  {titleCase(v)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Est. deliveries / month">
            <Input
              type="number"
              value={(form.estimated_deliveries_per_month as number) ?? ""}
              onChange={(e) =>
                setForm({ ...form, estimated_deliveries_per_month: Number(e.target.value) })
              }
            />
          </Field>
          <Field label="Est. revenue (cents)">
            <Input
              type="number"
              value={(form.estimated_revenue_cents as number) ?? ""}
              onChange={(e) =>
                setForm({ ...form, estimated_revenue_cents: Number(e.target.value) })
              }
            />
          </Field>
          <Field label="Current provider" className="col-span-2">
            <Input
              value={form.current_logistics_provider ?? ""}
              onChange={(e) => setForm({ ...form, current_logistics_provider: e.target.value })}
            />
          </Field>
        </div>
      </section>

      <section className="grid grid-cols-2 gap-4">
        <Field label="Status">
          <Select
            value={form.status ?? "new"}
            onChange={(e) => setForm({ ...form, status: e.target.value })}
          >
            {LEAD_STATUSES.map((s) => (
              <option key={s} value={s}>
                {titleCase(s)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Priority">
          <Select
            value={form.priority ?? "medium"}
            onChange={(e) => setForm({ ...form, priority: e.target.value })}
          >
            {LEAD_PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {titleCase(p)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Source">
          <Select
            value={form.source ?? "website"}
            onChange={(e) => setForm({ ...form, source: e.target.value })}
          >
            {LEAD_SOURCES.map((s) => (
              <option key={s} value={s}>
                {titleCase(s)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Expected close date">
          <Input
            type="date"
            value={(form.expected_close_date as string) ?? ""}
            onChange={(e) => setForm({ ...form, expected_close_date: e.target.value })}
          />
        </Field>
        <Field label="Internal notes" className="col-span-2">
          <Textarea
            value={form.internal_notes ?? ""}
            onChange={(e) => setForm({ ...form, internal_notes: e.target.value })}
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
                type="button"
                onClick={() => setCustomFields(customFields.filter((_, j) => j !== i))}
                className="rounded-lg p-2 text-muted hover:bg-gray-bg"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
          {customFields.length === 0 && (
            <p className="text-xs text-muted">
              Add any extra attribute — fleet size, account number, referral, etc.
            </p>
          )}
        </div>
      </section>
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

function Overview({ lead }: { lead: Lead }) {
  const a = lead.address as Record<string, string>;
  const addressParts = [a.street, a.city, a.province, a.postal_code, a.country].filter(Boolean);
  return (
    <div className="space-y-6">
      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">
          Company & contact
        </h3>
        <dl className="grid grid-cols-2 gap-4 md:grid-cols-3">
          <Detail label="Industry" value={lead.industry} />
          <Detail label="Business type" value={lead.business_type} />
          <Detail label="Website" value={lead.website} />
          <Detail label="Primary contact" value={lead.primary_contact_name} />
          <Detail label="Email" value={lead.email} />
          <Detail label="Phone" value={lead.phone} />
        </dl>
      </section>

      <section>
        <h3 className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted">
          <MapPin className="h-3.5 w-3.5" /> Address & service area
        </h3>
        <dl className="grid grid-cols-2 gap-4 md:grid-cols-3">
          <Detail label="Address" value={addressParts.length ? addressParts.join(", ") : null} />
          <Detail label="Service area" value={lead.service_area} />
          <Detail label="Current provider" value={lead.current_logistics_provider} />
        </dl>
      </section>

      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">
          Logistics opportunity
        </h3>
        <dl className="grid grid-cols-2 gap-4 md:grid-cols-3">
          <Detail
            label="Deliveries / month"
            value={lead.estimated_deliveries_per_month?.toString()}
          />
          <Detail label="Est. revenue" value={money(lead.estimated_revenue_cents)} />
          <Detail label="Preferred vehicle" value={titleCase(lead.preferred_vehicle ?? "")} />
          <Detail label="Expected close" value={shortDate(lead.expected_close_date)} />
          <Detail label="Created" value={shortDate(lead.created_at)} />
        </dl>
      </section>

      {lead.custom_fields && Object.keys(lead.custom_fields).length > 0 && (
        <section>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">
            Custom fields
          </h3>
          <dl className="grid grid-cols-2 gap-4 md:grid-cols-3">
            {Object.entries(lead.custom_fields).map(([key, value]) => (
              <Detail
                key={key}
                label={titleCase(key)}
                value={value == null ? null : String(value)}
              />
            ))}
          </dl>
        </section>
      )}

      {lead.internal_notes && (
        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
            Internal notes
          </h3>
          <p className="rounded-xl border border-primary/10 bg-gray-bg/40 p-3 text-sm text-primary">
            {lead.internal_notes}
          </p>
        </section>
      )}
    </div>
  );
}

function ConvertPrompt({
  message,
  onConvert,
  busy,
}: {
  message: string;
  onConvert: () => void;
  busy: boolean;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-primary/15 bg-gray-bg/30 px-6 py-12 text-center">
      <p className="max-w-md text-sm text-muted">{message}</p>
      <Button onClick={onConvert} disabled={busy}>
        Convert lead to company + deal <ArrowRight className="h-4 w-4" />
      </Button>
    </div>
  );
}

type DraftLine = { label: string; quantity: number; unit_price_cents: number };

function LeadQuotations({
  lead,
  onConvert,
  busy,
}: {
  lead: Lead;
  onConvert: () => void;
  busy: boolean;
}) {
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const { data } = useApiData(
    (t) =>
      lead.company_id
        ? crm.quotations(t, { company_id: lead.company_id })
        : Promise.resolve([] as Quotation[]),
    [lead.company_id, version]
  );
  const [creating, setCreating] = useState(false);
  const [lines, setLines] = useState<DraftLine[]>([
    { label: "", quantity: 1, unit_price_cents: 0 },
  ]);
  const [taxCents, setTaxCents] = useState(0);
  const [working, setWorking] = useState(false);

  const subtotal = lines.reduce((s, l) => s + l.quantity * l.unit_price_cents, 0);

  if (!lead.company_id) {
    return (
      <ConvertPrompt
        message="Quotations are generated against a company. Convert this lead first to start quoting."
        onConvert={onConvert}
        busy={busy}
      />
    );
  }

  async function create() {
    const valid = lines.filter((l) => l.label.trim());
    if (!valid.length) return;
    setWorking(true);
    try {
      const token = await getApiToken();
      await crm.createQuotation(token, {
        company_id: lead.company_id!,
        deal_id: lead.deal_id ?? undefined,
        line_items: valid,
        tax_cents: Number(taxCents) || 0,
      });
      setCreating(false);
      setLines([{ label: "", quantity: 1, unit_price_cents: 0 }]);
      setTaxCents(0);
      setVersion((v) => v + 1);
    } finally {
      setWorking(false);
    }
  }

  async function setStatus(q: Quotation, status: string) {
    const token = await getApiToken();
    await crm.setQuotationStatus(token, q.id, status);
    setVersion((v) => v + 1);
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button variant={creating ? "outline" : "primary"} onClick={() => setCreating(!creating)}>
          <Plus className="h-4 w-4" />
          {creating ? "Cancel" : "New quotation"}
        </Button>
      </div>

      {creating && (
        <div className="space-y-3 rounded-xl border border-primary/10 bg-gray-bg/30 p-4">
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
              <Button onClick={create} disabled={working}>
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
              <p className="text-xs text-muted">
                {q.line_items.length} items · {money(q.total_cents)}
              </p>
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

function LeadContracts({
  lead,
  onConvert,
  busy,
}: {
  lead: Lead;
  onConvert: () => void;
  busy: boolean;
}) {
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const { data } = useApiData(
    (t) =>
      lead.company_id
        ? crm.contracts(t, { company_id: lead.company_id })
        : Promise.resolve([] as Contract[]),
    [lead.company_id, version]
  );
  const [netTerms, setNetTerms] = useState("NET_30");
  const [value, setValue] = useState(0);
  const [working, setWorking] = useState(false);

  if (!lead.company_id) {
    return (
      <ConvertPrompt
        message="Contracts belong to a merchant company. Convert this lead to draft a contract."
        onConvert={onConvert}
        busy={busy}
      />
    );
  }

  async function create() {
    setWorking(true);
    try {
      const token = await getApiToken();
      await crm.createContract(token, {
        company_id: lead.company_id!,
        deal_id: lead.deal_id ?? undefined,
        net_terms: netTerms,
        value_cents: Number(value) || 0,
      });
      setValue(0);
      setVersion((v) => v + 1);
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-primary/10 bg-gray-bg/30 p-4">
        <Field label="Net terms">
          <Select value={netTerms} onChange={(e) => setNetTerms(e.target.value)} className="w-36">
            {["NET_15", "NET_30", "NET_45", "NET_60", "IMMEDIATE"].map((t) => (
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
        <Button onClick={create} disabled={working}>
          <Plus className="h-4 w-4" /> Draft contract
        </Button>
      </div>

      <div className="space-y-2">
        {(data ?? []).map((c) => (
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

function LeadCalendar({ leadId }: { leadId: string }) {
  const { data } = useApiData((t) => crm.tasks(t, { entity_id: leadId }), [leadId]);
  return <MiniCalendar tasks={data ?? []} />;
}

const CONTACT_ROLES = [
  "decision_maker",
  "primary_contact",
  "influencer",
  "accounts_payable",
  "warehouse_manager",
  "shipping_manager",
  "operations_manager",
  "purchasing",
  "owner",
];

function LeadContacts({
  lead,
  onConvert,
  busy,
}: {
  lead: Lead;
  onConvert: () => void;
  busy: boolean;
}) {
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const { data } = useApiData(
    (t) =>
      lead.company_id
        ? crm.contacts(t, { company_id: lead.company_id })
        : Promise.resolve([] as Contact[]),
    [lead.company_id, version]
  );
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState<Partial<Contact>>({ first_name: "", roles: [] });
  const [working, setWorking] = useState(false);

  if (!lead.company_id) {
    return (
      <ConvertPrompt
        message="Contacts are stored on the company record. Convert this lead to add and manage its contacts."
        onConvert={onConvert}
        busy={busy}
      />
    );
  }

  function toggleRole(role: string) {
    const roles = new Set(form.roles ?? []);
    if (roles.has(role)) roles.delete(role);
    else roles.add(role);
    setForm({ ...form, roles: [...roles] });
  }

  async function add() {
    if (!form.first_name) return;
    setWorking(true);
    try {
      const token = await getApiToken();
      await crm.createContact(token, { ...form, company_id: lead.company_id! });
      setForm({ first_name: "", roles: [] });
      setAdding(false);
      setVersion((v) => v + 1);
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted">
          {data?.length ?? 0} contact{(data?.length ?? 0) === 1 ? "" : "s"}
        </p>
        <Button variant={adding ? "outline" : "primary"} onClick={() => setAdding(!adding)}>
          <Plus className="h-4 w-4" />
          {adding ? "Cancel" : "Add contact"}
        </Button>
      </div>

      {adding && (
        <div className="space-y-3 rounded-xl border border-primary/10 bg-gray-bg/30 p-4">
          <div className="grid grid-cols-2 gap-3">
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
            <Field label="Department">
              <Input
                value={form.department ?? ""}
                onChange={(e) => setForm({ ...form, department: e.target.value })}
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
          </div>
          <Field label="Roles">
            <div className="flex flex-wrap gap-2">
              {CONTACT_ROLES.map((r) => {
                const on = (form.roles ?? []).includes(r);
                return (
                  <button
                    key={r}
                    type="button"
                    onClick={() => toggleRole(r)}
                    className={
                      "rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset transition-colors " +
                      (on
                        ? "bg-secondary text-white ring-secondary"
                        : "bg-white text-primary/70 ring-primary/15 hover:bg-gray-bg")
                    }
                  >
                    {titleCase(r)}
                  </button>
                );
              })}
            </div>
          </Field>
          <div className="flex justify-end">
            <Button onClick={add} disabled={working || !form.first_name}>
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
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-primary">
                {c.first_name} {c.last_name} {c.is_primary && <Badge tone="blue">Primary</Badge>}
              </p>
              <p className="truncate text-xs text-muted">
                {c.designation ?? "—"} · {c.email ?? c.phone ?? ""}
              </p>
            </div>
            {c.roles.length > 0 && (
              <div className="hidden flex-wrap justify-end gap-1 sm:flex">
                {c.roles.slice(0, 2).map((r) => (
                  <Badge key={r} tone="slate">
                    {titleCase(r)}
                  </Badge>
                ))}
                {c.roles.length > 2 && <Badge tone="slate">+{c.roles.length - 2}</Badge>}
              </div>
            )}
          </div>
        ))}
        {(!data || data.length === 0) && !adding && (
          <p className="py-6 text-center text-sm text-muted">No contacts yet.</p>
        )}
      </div>
    </div>
  );
}

function DealStageBar({ dealId, onChanged }: { dealId: string; onChanged?: () => void }) {
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const { data: deal } = useApiData((t) => crm.deal(t, dealId), [dealId, version]);
  const [busy, setBusy] = useState(false);

  async function change(stage: string) {
    setBusy(true);
    try {
      const token = await getApiToken();
      await crm.updateDeal(token, dealId, { stage });
      setVersion((v) => v + 1);
      onChanged?.();
    } finally {
      setBusy(false);
    }
  }

  if (!deal) return null;
  return (
    <div className="flex flex-wrap items-center gap-3 border-b border-primary/10 bg-secondary/5 px-6 py-2.5">
      <span className="text-xs font-semibold uppercase tracking-wide text-muted">Linked deal</span>
      <Badge tone={STATUS_TONE[deal.stage]}>
        {STAGE_LABELS[deal.stage] ?? titleCase(deal.stage)}
      </Badge>
      <span className="text-sm font-bold text-secondary">{money(deal.expected_revenue_cents)}</span>
      <span className="rounded-full bg-white px-2 py-0.5 text-xs font-medium text-primary/70">
        {deal.probability}% win
      </span>
      <div className="ml-auto flex items-center gap-2">
        <span className="text-xs text-muted">Change status</span>
        <Select
          value={deal.stage}
          onChange={(e) => change(e.target.value)}
          disabled={busy}
          className="w-44"
        >
          {DEAL_STAGES.map((s) => (
            <option key={s} value={s}>
              {STAGE_LABELS[s] ?? titleCase(s)}
            </option>
          ))}
        </Select>
      </div>
    </div>
  );
}
