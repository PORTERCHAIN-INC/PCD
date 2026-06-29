"use client";

import { useMemo, useState } from "react";
import { type ColumnDef } from "@tanstack/react-table";
import {
  Plus,
  Sparkles,
  SlidersHorizontal,
  X,
  CircleDot,
  Flag,
  Radio,
  Factory,
  Gauge,
  GitBranch,
  ArrowDownWideNarrow,
  MapPin,
} from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { crm, type Lead } from "@/lib/crm";
import { CrmTable } from "@/components/crm/CrmTable";
import { LeadDetailModal } from "@/components/crm/LeadDetailModal";
import { Combobox, Dropdown, FilterChip, ProvincePills } from "@/components/crm/filters";
import { Badge, Button, Drawer, Field, Input, Select, Textarea } from "@/components/crm/primitives";
import { STATUS_TONE, money, shortDate, titleCase } from "@/lib/crmFormat";

const PROVINCE_NAMES: Record<string, string> = {
  ON: "Ontario",
  QC: "Quebec",
  BC: "British Columbia",
  AB: "Alberta",
  MB: "Manitoba",
  SK: "Saskatchewan",
  NS: "Nova Scotia",
  NB: "New Brunswick",
  NL: "Newfoundland",
  PE: "PEI",
  NT: "Northwest Territories",
  YT: "Yukon",
  NU: "Nunavut",
};

const STATUSES = ["new", "contacted", "qualified", "nurturing", "unqualified", "converted"];
const PRIORITIES = ["low", "medium", "high", "urgent"];
const SOURCES = ["website", "for_business", "referral", "csv_import", "cold_outreach", "event"];
const VEHICLES = ["cargo_van", "refrigerated_van", "flatbed", "box_truck", "cargo_bike", "sedan"];

type Address = {
  street?: string;
  city?: string;
  province?: string;
  postal_code?: string;
  country?: string;
};

const blankLead = (): Partial<Lead> => ({
  company_name: "",
  industry: "",
  email: "",
  phone: "",
  primary_contact_name: "",
  source: "website",
  priority: "medium",
  status: "new",
  service_area: "",
  current_logistics_provider: "",
  business_type: "",
  website: "",
  preferred_vehicle: "",
});

export default function LeadsPage() {
  const { getApiToken } = useAdminAuth();

  // Server-side filters
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [source, setSource] = useState("");
  const [industry, setIndustry] = useState("");
  const [province, setProvince] = useState("");
  const [city, setCity] = useState("");
  const [converted, setConverted] = useState("");
  // Client-side filters
  const [minScore, setMinScore] = useState("");
  const [sortBy, setSortBy] = useState("newest");

  const [version, setVersion] = useState(0);
  const { data, error } = useApiData(
    (t) =>
      crm.leads(t, {
        status: status || undefined,
        priority: priority || undefined,
        source: source || undefined,
        industry: industry || undefined,
        province: province || undefined,
        city: city || undefined,
        converted: converted || undefined,
        limit: "10000",
      }),
    [status, priority, source, industry, province, city, converted, version]
  );
  const { data: facets } = useApiData((t) => crm.leadFacets(t), [version]);

  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<Partial<Lead>>(blankLead());
  const [addr, setAddr] = useState<Address>({});
  const [customFields, setCustomFields] = useState<Array<{ key: string; value: string }>>([]);
  const [selected, setSelected] = useState<Lead | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const refresh = () => setVersion((v) => v + 1);

  const rows = useMemo(() => {
    let r = data ? [...data] : [];
    if (minScore) r = r.filter((l) => l.lead_score >= Number(minScore));
    if (sortBy === "score") r.sort((a, b) => b.lead_score - a.lead_score);
    else if (sortBy === "revenue")
      r.sort((a, b) => (b.estimated_revenue_cents ?? 0) - (a.estimated_revenue_cents ?? 0));
    else if (sortBy === "company") r.sort((a, b) => a.company_name.localeCompare(b.company_name));
    return r;
  }, [data, minScore, sortBy]);

  const activeFilters =
    [status, priority, source, industry, province, city, converted, minScore].filter(Boolean)
      .length + (sortBy !== "newest" ? 1 : 0);

  function clearFilters() {
    setStatus("");
    setPriority("");
    setSource("");
    setIndustry("");
    setProvince("");
    setCity("");
    setConverted("");
    setMinScore("");
    setSortBy("newest");
  }

  const scoreLabel: Record<string, string> = {
    "70": "Hot (70+)",
    "40": "Warm (40+)",
    "1": "Scored (1+)",
  };
  const stageLabel: Record<string, string> = { false: "Not converted", true: "Converted" };

  async function submitCreate() {
    if (!form.company_name) return;
    setBusy(true);
    try {
      const token = await getApiToken();
      const custom_fields = Object.fromEntries(
        customFields.filter((f) => f.key.trim()).map((f) => [f.key.trim(), f.value])
      );
      await crm.createLead(token, {
        ...form,
        address: addr,
        custom_fields,
        estimated_deliveries_per_month: form.estimated_deliveries_per_month
          ? Number(form.estimated_deliveries_per_month)
          : null,
        estimated_revenue_cents: form.estimated_revenue_cents
          ? Number(form.estimated_revenue_cents)
          : null,
      });
      setCreating(false);
      setForm(blankLead());
      setAddr({});
      setCustomFields([]);
      refresh();
    } finally {
      setBusy(false);
    }
  }

  async function convert(lead: Lead) {
    setBusy(true);
    try {
      const token = await getApiToken();
      const res = await crm.convertLead(token, lead.id, { create_deal: true });
      setToast(
        `Converted "${lead.company_name}" to a company${res.deal_id ? " and opened a deal" : ""}.`
      );
      const fresh = await crm.leads(token, { limit: "10000" });
      setSelected(fresh.find((l) => l.id === lead.id) ?? null);
      refresh();
    } finally {
      setBusy(false);
    }
  }

  const columns = useMemo<ColumnDef<Lead, unknown>[]>(
    () => [
      {
        accessorKey: "company_name",
        header: "Company",
        cell: ({ row }) => (
          <div>
            <p className="font-semibold text-primary">{row.original.company_name}</p>
            <p className="text-xs text-muted">{row.original.industry ?? "—"}</p>
          </div>
        ),
      },
      {
        accessorKey: "primary_contact_name",
        header: "Contact",
        cell: ({ row }) => (
          <div>
            <p>{row.original.primary_contact_name ?? "—"}</p>
            <p className="text-xs text-muted">{row.original.email ?? row.original.phone ?? ""}</p>
          </div>
        ),
      },
      {
        id: "location",
        header: "Location",
        cell: ({ row }) => {
          const a = row.original.address as Record<string, string>;
          const parts = [a?.city, a?.province].filter(Boolean);
          return (
            <div>
              <p>{parts.length ? parts.join(", ") : (row.original.service_area ?? "—")}</p>
              {a?.postal_code && <p className="text-xs text-muted">{a.postal_code}</p>}
            </div>
          );
        },
      },
      {
        accessorKey: "source",
        header: "Source",
        cell: ({ getValue }) => titleCase(String(getValue())),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ getValue }) => (
          <Badge tone={STATUS_TONE[String(getValue())]}>{titleCase(String(getValue()))}</Badge>
        ),
      },
      {
        accessorKey: "priority",
        header: "Priority",
        cell: ({ getValue }) => (
          <Badge tone={STATUS_TONE[String(getValue())]}>{titleCase(String(getValue()))}</Badge>
        ),
      },
      {
        accessorKey: "lead_score",
        header: "Score",
        cell: ({ getValue }) => {
          const s = Number(getValue());
          return (
            <Badge tone={s >= 70 ? "green" : s >= 40 ? "amber" : "slate"}>
              <Sparkles className="h-3 w-3" />
              {s}
            </Badge>
          );
        },
      },
      {
        accessorKey: "estimated_revenue_cents",
        header: "Est. Revenue",
        cell: ({ getValue }) => money(getValue() as number),
      },
      {
        accessorKey: "created_at",
        header: "Created",
        cell: ({ getValue }) => shortDate(String(getValue())),
      },
    ],
    []
  );

  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div className="space-y-4">
      {toast && (
        <div className="flex items-center justify-between rounded-xl border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-700">
          {toast}
          <button onClick={() => setToast(null)}>
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Modern filter panel */}
      <div className="space-y-3 rounded-2xl border border-primary/10 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2 text-sm font-semibold text-primary">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-secondary/10 text-secondary">
              <SlidersHorizontal className="h-4 w-4" />
            </span>
            Filters
            {activeFilters > 0 && <Badge tone="blue">{activeFilters} active</Badge>}
            <span className="text-xs font-normal text-muted">· {rows.length} leads</span>
          </span>
          {activeFilters > 0 && (
            <Button variant="ghost" onClick={clearFilters} className="text-xs">
              <X className="h-4 w-4" />
              Clear all
            </Button>
          )}
        </div>

        {/* Province pills */}
        <div className="flex items-start gap-2">
          <span className="mt-1.5 flex shrink-0 items-center gap-1 text-xs font-medium text-muted">
            <MapPin className="h-3.5 w-3.5" /> Province
          </span>
          <ProvincePills
            provinces={facets?.provinces ?? []}
            value={province}
            onChange={setProvince}
          />
        </div>

        {/* Dropdown row */}
        <div className="flex flex-wrap items-center gap-2 border-t border-primary/5 pt-3">
          <Combobox
            label="City"
            icon={<MapPin className="h-4 w-4" />}
            value={city}
            onChange={setCity}
            options={(facets?.cities ?? []).map((c) => ({
              value: c.name,
              label: c.name,
              hint: c.count,
            }))}
          />
          <Dropdown
            label="Status"
            icon={<CircleDot className="h-4 w-4" />}
            value={status}
            onChange={setStatus}
            options={STATUSES.map((s) => ({ value: s, label: titleCase(s) }))}
          />
          <Dropdown
            label="Priority"
            icon={<Flag className="h-4 w-4" />}
            value={priority}
            onChange={setPriority}
            options={PRIORITIES.map((p) => ({ value: p, label: titleCase(p) }))}
          />
          <Dropdown
            label="Source"
            icon={<Radio className="h-4 w-4" />}
            value={source}
            onChange={setSource}
            options={(facets?.sources?.length ? facets.sources : SOURCES).map((s) => ({
              value: s,
              label: titleCase(s),
            }))}
          />
          <Dropdown
            label="Industry"
            icon={<Factory className="h-4 w-4" />}
            value={industry}
            onChange={setIndustry}
            options={(facets?.industries ?? []).map((i) => ({ value: i, label: i }))}
          />
          <Dropdown
            label="Score"
            icon={<Gauge className="h-4 w-4" />}
            value={minScore}
            onChange={setMinScore}
            allLabel="Any score"
            options={[
              { value: "70", label: "Hot (70+)" },
              { value: "40", label: "Warm (40+)" },
              { value: "1", label: "Scored (1+)" },
            ]}
          />
          <Dropdown
            label="Stage"
            icon={<GitBranch className="h-4 w-4" />}
            value={converted}
            onChange={setConverted}
            allLabel="Any stage"
            options={[
              { value: "false", label: "Not converted" },
              { value: "true", label: "Converted" },
            ]}
          />
          <Dropdown
            label="Sort"
            icon={<ArrowDownWideNarrow className="h-4 w-4" />}
            value={sortBy === "newest" ? "" : sortBy}
            onChange={(v) => setSortBy(v || "newest")}
            allLabel="Newest"
            options={[
              { value: "score", label: "Lead score" },
              { value: "revenue", label: "Est. revenue" },
              { value: "company", label: "Company A–Z" },
            ]}
          />
        </div>

        {/* Active filter chips */}
        {activeFilters > 0 && (
          <div className="flex flex-wrap items-center gap-2 border-t border-primary/5 pt-3">
            {province && (
              <FilterChip
                label={`Province: ${PROVINCE_NAMES[province] ?? province}`}
                onRemove={() => setProvince("")}
              />
            )}
            {city && <FilterChip label={`City: ${city}`} onRemove={() => setCity("")} />}
            {status && (
              <FilterChip label={`Status: ${titleCase(status)}`} onRemove={() => setStatus("")} />
            )}
            {priority && (
              <FilterChip
                label={`Priority: ${titleCase(priority)}`}
                onRemove={() => setPriority("")}
              />
            )}
            {source && (
              <FilterChip label={`Source: ${titleCase(source)}`} onRemove={() => setSource("")} />
            )}
            {industry && (
              <FilterChip label={`Industry: ${industry}`} onRemove={() => setIndustry("")} />
            )}
            {minScore && (
              <FilterChip
                label={scoreLabel[minScore] ?? minScore}
                onRemove={() => setMinScore("")}
              />
            )}
            {converted && (
              <FilterChip
                label={stageLabel[converted] ?? converted}
                onRemove={() => setConverted("")}
              />
            )}
            {sortBy !== "newest" && (
              <FilterChip label={`Sort: ${sortBy}`} onRemove={() => setSortBy("newest")} />
            )}
          </div>
        )}
      </div>

      <CrmTable
        data={rows}
        columns={columns}
        onRowClick={setSelected}
        searchPlaceholder="Search company, contact, area…"
        emptyTitle="No leads match these filters"
        emptyHint="Every business inquiry becomes a lead. Add one or adjust the filters above."
        toolbar={
          <Button onClick={() => setCreating(true)}>
            <Plus className="h-4 w-4" />
            New Lead
          </Button>
        }
      />

      {/* Create drawer */}
      <Drawer
        open={creating}
        onClose={() => setCreating(false)}
        title="New lead"
        footer={
          <>
            <Button variant="outline" onClick={() => setCreating(false)}>
              Cancel
            </Button>
            <Button onClick={submitCreate} disabled={busy || !form.company_name}>
              Create lead
            </Button>
          </>
        }
      >
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
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Address</p>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Street" className="col-span-2">
                <Input
                  value={addr.street ?? ""}
                  onChange={(e) => setAddr({ ...addr, street: e.target.value })}
                />
              </Field>
              <Field label="City">
                <Input
                  value={addr.city ?? ""}
                  onChange={(e) => setAddr({ ...addr, city: e.target.value })}
                />
              </Field>
              <Field label="Province">
                <Input
                  value={addr.province ?? ""}
                  onChange={(e) => setAddr({ ...addr, province: e.target.value })}
                />
              </Field>
              <Field label="Postal code">
                <Input
                  value={addr.postal_code ?? ""}
                  onChange={(e) => setAddr({ ...addr, postal_code: e.target.value })}
                />
              </Field>
              <Field label="Country">
                <Input
                  value={addr.country ?? "Canada"}
                  onChange={(e) => setAddr({ ...addr, country: e.target.value })}
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
                  {VEHICLES.map((v) => (
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
            <Field label="Source">
              <Select
                value={form.source ?? "website"}
                onChange={(e) => setForm({ ...form, source: e.target.value })}
              >
                {SOURCES.map((s) => (
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
                {PRIORITIES.map((p) => (
                  <option key={p} value={p}>
                    {titleCase(p)}
                  </option>
                ))}
              </Select>
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
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                Custom fields
              </p>
              <Button
                variant="ghost"
                className="text-xs"
                onClick={() => setCustomFields([...customFields, { key: "", value: "" }])}
              >
                <Plus className="h-4 w-4" />
                Add field
              </Button>
            </div>
            {customFields.length === 0 && (
              <p className="text-xs text-muted">
                Capture anything extra — fleet size, referral, account number, etc.
              </p>
            )}
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
            </div>
          </section>
        </div>
      </Drawer>

      {/* Tabbed detail modal */}
      <LeadDetailModal
        lead={selected}
        onClose={() => setSelected(null)}
        onConvert={convert}
        busy={busy}
        onChanged={refresh}
      />
    </div>
  );
}
