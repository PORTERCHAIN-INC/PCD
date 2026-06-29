"use client";

import { useMemo, useState } from "react";
import { type ColumnDef } from "@tanstack/react-table";
import {
  Plus,
  Building2,
  Pin,
  SlidersHorizontal,
  X,
  MapPin,
  CircleDot,
  Factory,
  Target,
  ArrowDownWideNarrow,
  Rocket,
  Users,
  TrendingUp,
} from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { crm, type Company } from "@/lib/crm";
import { CrmTable } from "@/components/crm/CrmTable";
import { CompanyDetailModal } from "@/components/crm/CompanyDetailModal";
import { Combobox, Dropdown, FilterChip, ProvincePills } from "@/components/crm/filters";
import { Badge, Button, Drawer, Field, Input, Select } from "@/components/crm/primitives";
import { STATUS_TONE, money, titleCase } from "@/lib/crmFormat";

const MERCHANT_STATUSES = ["lead", "prospect", "negotiating", "active_merchant", "churned"];

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

const blank = (): Partial<Company> => ({
  legal_name: "",
  industry: "",
  email: "",
  merchant_status: "lead",
});

export default function CompaniesPage() {
  const { getApiToken } = useAdminAuth();

  const [status, setStatus] = useState("");
  const [industry, setIndustry] = useState("");
  const [province, setProvince] = useState("");
  const [city, setCity] = useState("");
  const [minValue, setMinValue] = useState("");
  const [sortBy, setSortBy] = useState("recent");
  const [version, setVersion] = useState(0);

  const { data, error } = useApiData(
    (t) =>
      crm.companies(t, {
        merchant_status: status || undefined,
        industry: industry || undefined,
        province: province || undefined,
        city: city || undefined,
        limit: "10000",
      }),
    [status, industry, province, city, version]
  );
  const { data: facets } = useApiData((t) => crm.companyFacets(t), [version]);
  const { data: stats } = useApiData((t) => crm.companyStats(t), [version]);

  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<Partial<Company>>(blank());
  const [selected, setSelected] = useState<Company | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = () => setVersion((v) => v + 1);

  const rows = useMemo(() => {
    let r = data ? [...data] : [];
    if (minValue) r = r.filter((c) => (c.estimated_monthly_revenue_cents ?? 0) >= Number(minValue));
    if (sortBy === "value")
      r.sort(
        (a, b) =>
          (b.estimated_monthly_revenue_cents ?? 0) - (a.estimated_monthly_revenue_cents ?? 0)
      );
    else if (sortBy === "name")
      r.sort((a, b) =>
        (a.operating_name || a.legal_name).localeCompare(b.operating_name || b.legal_name)
      );
    return r;
  }, [data, minValue, sortBy]);

  const activeFilters =
    [status, industry, province, city, minValue].filter(Boolean).length +
    (sortBy !== "recent" ? 1 : 0);

  function clearFilters() {
    setStatus("");
    setIndustry("");
    setProvince("");
    setCity("");
    setMinValue("");
    setSortBy("recent");
  }

  async function submitCreate() {
    if (!form.legal_name) return;
    setBusy(true);
    try {
      const token = await getApiToken();
      await crm.createCompany(token, form);
      setCreating(false);
      setForm(blank());
      refresh();
    } finally {
      setBusy(false);
    }
  }

  const columns = useMemo<ColumnDef<Company, unknown>[]>(
    () => [
      {
        accessorKey: "legal_name",
        header: "Company",
        cell: ({ row }) => (
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-secondary/10 text-secondary">
              <Building2 className="h-4 w-4" />
            </span>
            <div>
              <p className="flex items-center gap-1 font-semibold text-primary">
                {row.original.operating_name || row.original.legal_name}
                {row.original.is_pinned && <Pin className="h-3 w-3 text-secondary" />}
              </p>
              <p className="text-xs text-muted">{row.original.industry ?? "—"}</p>
            </div>
          </div>
        ),
      },
      {
        accessorKey: "merchant_status",
        header: "Status",
        cell: ({ getValue }) => (
          <Badge tone={STATUS_TONE[String(getValue())]}>{titleCase(String(getValue()))}</Badge>
        ),
      },
      {
        id: "location",
        header: "Location",
        cell: ({ row }) => {
          const a = row.original.address as Record<string, string>;
          const parts = [a?.city, a?.province].filter(Boolean);
          return parts.length ? parts.join(", ") : (row.original.service_area ?? "—");
        },
      },
      {
        accessorKey: "estimated_deliveries_per_month",
        header: "Deliveries/mo",
        cell: ({ getValue }) => (getValue() ? String(getValue()) : "—"),
      },
      {
        accessorKey: "estimated_monthly_revenue_cents",
        header: "Monthly value",
        cell: ({ getValue }) => money(getValue() as number),
      },
    ],
    []
  );

  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div className="space-y-4">
      {/* Stats strip */}
      {stats && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile icon={Building2} label="Total companies" value={stats.total.toLocaleString()} />
          <StatTile
            icon={Rocket}
            label="Active merchants"
            value={String(stats.active_merchants)}
            accent="text-green-600"
          />
          <StatTile
            icon={Users}
            label="Conversion rate"
            value={`${stats.conversion_rate_percent}%`}
          />
          <StatTile
            icon={TrendingUp}
            label="Monthly pipeline"
            value={money(stats.monthly_pipeline_value_cents)}
            accent="text-secondary"
          />
        </div>
      )}

      {/* Filter panel */}
      <div className="space-y-3 rounded-2xl border border-primary/10 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2 text-sm font-semibold text-primary">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-secondary/10 text-secondary">
              <SlidersHorizontal className="h-4 w-4" />
            </span>
            Filters
            {activeFilters > 0 && <Badge tone="blue">{activeFilters} active</Badge>}
            <span className="text-xs font-normal text-muted">
              · {rows.length.toLocaleString()} companies
            </span>
          </span>
          {activeFilters > 0 && (
            <Button variant="ghost" onClick={clearFilters} className="text-xs">
              <X className="h-4 w-4" /> Clear all
            </Button>
          )}
        </div>

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
            options={MERCHANT_STATUSES.map((s) => ({ value: s, label: titleCase(s) }))}
          />
          <Dropdown
            label="Industry"
            icon={<Factory className="h-4 w-4" />}
            value={industry}
            onChange={setIndustry}
            options={(facets?.industries ?? []).map((i) => ({ value: i, label: i }))}
          />
          <Dropdown
            label="Min value"
            icon={<Target className="h-4 w-4" />}
            value={minValue}
            onChange={setMinValue}
            allLabel="Any value"
            options={[
              { value: "100000", label: "$1k+/mo" },
              { value: "1000000", label: "$10k+/mo" },
              { value: "5000000", label: "$50k+/mo" },
            ]}
          />
          <Dropdown
            label="Sort"
            icon={<ArrowDownWideNarrow className="h-4 w-4" />}
            value={sortBy === "recent" ? "" : sortBy}
            onChange={(v) => setSortBy(v || "recent")}
            allLabel="Recent"
            options={[
              { value: "value", label: "Monthly value" },
              { value: "name", label: "Name A–Z" },
            ]}
          />
        </div>

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
            {industry && (
              <FilterChip label={`Industry: ${industry}`} onRemove={() => setIndustry("")} />
            )}
            {minValue && (
              <FilterChip
                label={`Min ${money(Number(minValue))}/mo`}
                onRemove={() => setMinValue("")}
              />
            )}
            {sortBy !== "recent" && (
              <FilterChip label={`Sort: ${sortBy}`} onRemove={() => setSortBy("recent")} />
            )}
          </div>
        )}
      </div>

      <CrmTable
        data={rows}
        columns={columns}
        onRowClick={setSelected}
        searchPlaceholder="Search companies…"
        emptyTitle="No companies match these filters"
        emptyHint="Convert a lead or add a company to begin tracking the account."
        toolbar={
          <Button onClick={() => setCreating(true)}>
            <Plus className="h-4 w-4" />
            New Company
          </Button>
        }
      />

      {/* Create drawer */}
      <Drawer
        open={creating}
        onClose={() => setCreating(false)}
        title="New company"
        footer={
          <>
            <Button variant="outline" onClick={() => setCreating(false)}>
              Cancel
            </Button>
            <Button onClick={submitCreate} disabled={busy || !form.legal_name}>
              Create company
            </Button>
          </>
        }
      >
        <div className="grid grid-cols-2 gap-4">
          <Field label="Legal name *" className="col-span-2">
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
          <Field label="Service area">
            <Input
              value={form.service_area ?? ""}
              onChange={(e) => setForm({ ...form, service_area: e.target.value })}
            />
          </Field>
          <Field label="Merchant status">
            <Select
              value={form.merchant_status ?? "lead"}
              onChange={(e) => setForm({ ...form, merchant_status: e.target.value })}
            >
              {MERCHANT_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {titleCase(s)}
                </option>
              ))}
            </Select>
          </Field>
        </div>
      </Drawer>

      {/* Tabbed company modal */}
      <CompanyDetailModal
        company={selected}
        onClose={() => setSelected(null)}
        onChanged={refresh}
      />
    </div>
  );
}

function StatTile({
  icon: Icon,
  label,
  value,
  accent = "text-secondary",
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-muted">{label}</p>
        <Icon className={`h-4 w-4 ${accent}`} />
      </div>
      <p className="mt-2 text-2xl font-bold text-primary">{value}</p>
    </div>
  );
}
