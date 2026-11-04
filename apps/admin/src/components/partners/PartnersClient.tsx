"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Building2, CheckCircle2, PackageOpen, PauseCircle, Plus, Truck } from "lucide-react";
import { TableSkeleton } from "@porterchain/ui/loading";
import {
  Badge,
  Button,
  Drawer,
  EmptyState,
  Field,
  Input,
  SectionCard,
  Select,
} from "@/components/crm/primitives";
import { FilterChip } from "@/components/crm/filters";
import {
  CsvButton,
  FacetButton,
  SearchBox,
  SortHeader,
  StatTile,
  sortRows,
  type Sort,
} from "@/components/console/ConsoleKit";
import AdminPage from "@/components/layout/AdminPage";
import { useShowMore } from "@/components/layout/ShowMore";
import { PartnerJobsPanel } from "@/components/dispatch/PartnerJobsPanel";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { money, shortDate } from "@/lib/crmFormat";
import { dispatch, type LogisticsPartner, type PartnerStats } from "@/lib/dispatch";
import { EMPTY_PARTNER, PARTNER_KIND_LABEL, parseCoverage, partnerError } from "@/lib/partners";

type Kind = LogisticsPartner["kind"];
type StatusFilter = "" | "active" | "paused";
type SortKey = "name" | "kind" | "rate" | "transit" | "open" | "delivered" | "spend";

const NONE: PartnerStats = {
  open_legs: 0,
  delivered_recent: 0,
  cost_recent_cents: 0,
  last_leg_at: null,
};
const dollars = (c: number) => (c / 100).toFixed(2);

/** Doc 75 Network → Partners: couriers, linehaul, 3PL, warehouses and CHAs. */
export function PartnersClient() {
  const { getApiToken } = useAdminAuth();
  const [items, setItems] = useState<LogisticsPartner[] | null>(null);
  const [stats, setStats] = useState<Record<string, PartnerStats>>({});
  const [edit, setEdit] = useState<LogisticsPartner | null>(null);
  const [cov, setCov] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [formErr, setFormErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [q, setQ] = useState("");
  const [kind, setKind] = useState<Kind | "">("");
  const [status, setStatus] = useState<StatusFilter>("");
  const [sort, setSort] = useState<Sort<SortKey>>({ key: "name", dir: "asc" });
  const [picked, setPicked] = useState<Set<string>>(new Set());

  const load = useCallback(async () => {
    const t = await getApiToken();
    const [list, st] = await Promise.all([
      dispatch.partners(t),
      dispatch.partnerStats(t).catch(() => null),
    ]);
    setItems(list.items);
    setStats(st?.items ?? {});
  }, [getApiToken]);
  useEffect(() => {
    void load().catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }, [load]);

  const all = useMemo(() => items ?? [], [items]);
  const st = (p: LogisticsPartner) => (p.id && stats[p.id]) || NONE;
  const kpi = useMemo(() => {
    const active = all.filter((p) => p.active).length;
    let open = 0;
    let spend = 0;
    for (const p of all) {
      const s = (p.id && stats[p.id]) || NONE;
      open += s.open_legs;
      spend += s.cost_recent_cents;
    }
    return { total: all.length, active, paused: all.length - active, open, spend };
  }, [all, stats]);

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const filtered = all.filter(
      (p) =>
        (!kind || p.kind === kind) &&
        (!status || (status === "active" ? p.active : !p.active)) &&
        (!needle ||
          p.name.toLowerCase().includes(needle) ||
          (p.contact_email ?? "").toLowerCase().includes(needle) ||
          p.fsa_coverage.some((f) => f.toLowerCase().startsWith(needle)))
    );
    return sortRows(filtered, sort, (p, k) => {
      const s = (p.id && stats[p.id]) || NONE;
      return {
        name: p.name.toLowerCase(),
        kind: PARTNER_KIND_LABEL[p.kind] ?? p.kind,
        rate: p.rate_per_kg_cents,
        transit: p.transit_days,
        open: s.open_legs,
        delivered: s.delivered_recent,
        spend: s.cost_recent_cents,
      }[k];
    });
  }, [all, kind, status, q, sort, stats]);
  const page = useShowMore(rows, 25);
  const kinds = Object.keys(PARTNER_KIND_LABEL) as Kind[];
  const kindCount = (k: Kind) => all.filter((p) => p.kind === k).length;

  function open(p: LogisticsPartner) {
    setEdit({ ...p });
    setCov((p.fsa_coverage ?? []).join(" "));
    setFormErr(null);
  }

  async function save() {
    if (!edit) return;
    const body = { ...edit, fsa_coverage: parseCoverage(cov) };
    const invalid = partnerError(body);
    if (invalid) return setFormErr(invalid);
    setSaving(true);
    try {
      await dispatch.savePartner(await getApiToken(), body);
      setEdit(null);
      await load();
    } catch (e) {
      setFormErr(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function bulk(active: boolean) {
    setErr(null);
    try {
      await dispatch.partnersBulkActive(await getApiToken(), [...picked], active);
      setPicked(new Set());
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Update failed");
    }
  }

  const toggle = (id: string) =>
    setPicked((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  const visibleIds = page.visible.map((p) => p.id).filter(Boolean) as string[];
  const allPicked = visibleIds.length > 0 && visibleIds.every((id) => picked.has(id));
  const num = (v: string) => (v === "" ? null : Number(v));

  const csvRows = rows.map((p) => {
    const s = st(p);
    return [
      p.name,
      PARTNER_KIND_LABEL[p.kind] ?? p.kind,
      p.active ? "Active" : "Paused",
      p.fsa_coverage.join(" "),
      dollars(p.rate_per_kg_cents),
      dollars(p.min_charge_cents),
      String(p.transit_days),
      p.cutoff_local ?? "",
      p.contact_email ?? "",
      String(s.open_legs),
      String(s.delivered_recent),
      dollars(s.cost_recent_cents),
    ];
  });

  return (
    <AdminPage
      title="Partners"
      description="Couriers, linehaul, 3PL and customs agents we hand legs to."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link
            href="/partners/jobs"
            className="inline-flex items-center gap-2 rounded-xl border border-primary/15 bg-white px-3.5 py-2 text-sm font-medium text-primary hover:bg-gray-bg"
          >
            Partner jobs
          </Link>
          <CsvButton
            filename="partners.csv"
            headers={[
              "Name",
              "Kind",
              "Status",
              "Coverage",
              "Rate/kg",
              "Minimum",
              "Transit days",
              "Cutoff",
              "Ops email",
              "Open legs",
              "Delivered 30d",
              "Spend 30d",
            ]}
            rows={csvRows}
          />
          <Button onClick={() => open(EMPTY_PARTNER)}>
            <Plus className="h-4 w-4" /> Add partner
          </Button>
        </div>
      }
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <StatTile
          icon={Building2}
          label="Partners"
          value={String(kpi.total)}
          active={status === ""}
          onClick={() => setStatus("")}
        />
        <StatTile
          icon={CheckCircle2}
          label="Active"
          value={String(kpi.active)}
          accent="text-green-600"
          active={status === "active"}
          onClick={() => setStatus(status === "active" ? "" : "active")}
        />
        <StatTile
          icon={PauseCircle}
          label="Paused"
          value={String(kpi.paused)}
          accent="text-slate-600"
          active={status === "paused"}
          onClick={() => setStatus(status === "paused" ? "" : "paused")}
        />
        <StatTile icon={Truck} label="Open legs" value={String(kpi.open)} accent="text-sky-600" />
        <StatTile icon={PackageOpen} label="Spend (30d, est.)" value={money(kpi.spend)} />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <SearchBox value={q} onChange={setQ} placeholder="Search name, email or FSA…" />
        <FacetButton active={kind === ""} onClick={() => setKind("")}>
          All
        </FacetButton>
        {kinds.map((k) => (
          <FacetButton key={k} active={kind === k} onClick={() => setKind(kind === k ? "" : k)}>
            {PARTNER_KIND_LABEL[k]} <span className="text-muted">{kindCount(k)}</span>
          </FacetButton>
        ))}
      </div>
      {(kind || status) && (
        <div className="flex flex-wrap gap-2">
          {kind && (
            <FilterChip label={`Kind: ${PARTNER_KIND_LABEL[kind]}`} onRemove={() => setKind("")} />
          )}
          {status && (
            <FilterChip
              label={`Status: ${status === "active" ? "Active" : "Paused"}`}
              onRemove={() => setStatus("")}
            />
          )}
        </div>
      )}
      {err ? (
        <p role="alert" className="text-sm text-red-700">
          {err}
        </p>
      ) : null}

      <SectionCard
        title={`Directory (${rows.length})`}
        action={
          picked.size > 0 ? (
            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted">{picked.size} selected</span>
              <Button onClick={() => void bulk(true)}>Activate</Button>
              <Button onClick={() => void bulk(false)}>Pause</Button>
            </div>
          ) : undefined
        }
      >
        {items === null && !err ? (
          <TableSkeleton rows={6} />
        ) : rows.length === 0 ? (
          <EmptyState
            title={all.length === 0 ? "No partners yet" : "No partners match"}
            hint={
              all.length === 0
                ? "Add the couriers, linehaul carriers and 3PLs you hand legs to."
                : "Clear the search or filters."
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-primary/10 bg-gray-bg/40 text-xs uppercase text-muted">
                <tr>
                  <th className="w-10 px-4 py-2">
                    <input
                      type="checkbox"
                      aria-label="Select all shown"
                      checked={allPicked}
                      onChange={() => setPicked(allPicked ? new Set() : new Set(visibleIds))}
                    />
                  </th>
                  <SortHeader label="Partner" k="name" sort={sort} onSort={setSort} />
                  <SortHeader label="Kind" k="kind" sort={sort} onSort={setSort} />
                  <th className="hidden px-4 py-2 lg:table-cell">Coverage</th>
                  <SortHeader
                    label="Rate"
                    k="rate"
                    sort={sort}
                    onSort={setSort}
                    className="hidden md:table-cell"
                  />
                  <SortHeader
                    label="Transit"
                    k="transit"
                    sort={sort}
                    onSort={setSort}
                    className="hidden md:table-cell"
                  />
                  <SortHeader label="Open" k="open" sort={sort} onSort={setSort} />
                  <SortHeader
                    label="Delivered 30d"
                    k="delivered"
                    sort={sort}
                    onSort={setSort}
                    className="hidden sm:table-cell"
                  />
                  <th className="px-4 py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {page.visible.map((p) => {
                  const s = st(p);
                  return (
                    <tr
                      key={p.id}
                      className="cursor-pointer border-b border-primary/5 hover:bg-gray-bg/40"
                      onClick={() => open(p)}
                    >
                      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                        {p.id && (
                          <input
                            type="checkbox"
                            aria-label={`Select ${p.name}`}
                            checked={picked.has(p.id)}
                            onChange={() => toggle(p.id!)}
                          />
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <p className="font-medium text-primary">{p.name}</p>
                        <p className="text-xs text-muted">{p.contact_email || "No ops email"}</p>
                      </td>
                      <td className="px-4 py-3">{PARTNER_KIND_LABEL[p.kind] ?? p.kind}</td>
                      <td className="hidden max-w-[220px] truncate px-4 py-3 text-xs lg:table-cell">
                        {p.fsa_coverage.join(" ") || "—"}
                      </td>
                      <td className="hidden px-4 py-3 tabular-nums md:table-cell">
                        ${dollars(p.rate_per_kg_cents)}/kg
                        <span className="block text-xs text-muted">
                          min ${dollars(p.min_charge_cents)}
                        </span>
                      </td>
                      <td className="hidden px-4 py-3 md:table-cell">
                        {p.transit_days} d
                        {p.cutoff_local ? (
                          <span className="block text-xs text-muted">cutoff {p.cutoff_local}</span>
                        ) : null}
                      </td>
                      <td className="px-4 py-3 tabular-nums">{s.open_legs}</td>
                      <td className="hidden px-4 py-3 tabular-nums sm:table-cell">
                        {s.delivered_recent}
                        {s.last_leg_at ? (
                          <span className="block text-xs text-muted">
                            last {shortDate(s.last_leg_at)}
                          </span>
                        ) : null}
                      </td>
                      <td className="px-4 py-3">
                        <Badge tone={p.active ? "green" : "slate"}>
                          {p.active ? "Active" : "Paused"}
                        </Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {page.more}
          </div>
        )}
      </SectionCard>

      <Drawer
        open={edit !== null}
        onClose={() => setEdit(null)}
        title={edit?.id ? `Edit ${edit.name}` : "Add partner"}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setEdit(null)}>Cancel</Button>
            <Button onClick={() => void save()} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </div>
        }
      >
        {edit && (
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Name" className="sm:col-span-2">
              <Input
                value={edit.name}
                onChange={(e) => setEdit({ ...edit, name: e.target.value })}
              />
            </Field>
            <Field label="Kind">
              <Select
                value={edit.kind}
                onChange={(e) => setEdit({ ...edit, kind: e.target.value as Kind })}
              >
                {kinds.map((k) => (
                  <option key={k} value={k}>
                    {PARTNER_KIND_LABEL[k]}
                  </option>
                ))}
              </Select>
            </Field>
            <Field
              label="Ops desk email"
              hint="Job sheets and email drafts go here. You send them."
            >
              <Input
                type="email"
                value={edit.contact_email ?? ""}
                onChange={(e) => setEdit({ ...edit, contact_email: e.target.value || null })}
              />
            </Field>
            <Field label="FSA coverage" hint="e.g. M L4 K" className="sm:col-span-2">
              <Input value={cov} onChange={(e) => setCov(e.target.value)} />
            </Field>
            <Field label="Rate per kg ($)">
              <Input
                type="number"
                min={0}
                step="0.01"
                value={dollars(edit.rate_per_kg_cents)}
                onChange={(e) =>
                  setEdit({
                    ...edit,
                    rate_per_kg_cents: Math.round((Number(e.target.value) || 0) * 100),
                  })
                }
              />
            </Field>
            <Field label="Minimum charge ($)">
              <Input
                type="number"
                min={0}
                step="0.01"
                value={dollars(edit.min_charge_cents)}
                onChange={(e) =>
                  setEdit({
                    ...edit,
                    min_charge_cents: Math.round((Number(e.target.value) || 0) * 100),
                  })
                }
              />
            </Field>
            <Field label="Transit days">
              <Input
                type="number"
                min={0}
                value={edit.transit_days}
                onChange={(e) => setEdit({ ...edit, transit_days: Number(e.target.value) || 0 })}
              />
            </Field>
            <Field label="Cutoff (local)">
              <Input
                type="time"
                value={edit.cutoff_local ?? ""}
                onChange={(e) => setEdit({ ...edit, cutoff_local: e.target.value || null })}
              />
            </Field>
            <Field
              label="Latitude"
              hint={edit.kind === "warehouse" ? "Required for warehouses" : undefined}
            >
              <Input
                inputMode="decimal"
                value={edit.lat ?? ""}
                onChange={(e) => setEdit({ ...edit, lat: num(e.target.value) })}
              />
            </Field>
            <Field label="Longitude">
              <Input
                inputMode="decimal"
                value={edit.lng ?? ""}
                onChange={(e) => setEdit({ ...edit, lng: num(e.target.value) })}
              />
            </Field>
            <label className="flex items-center gap-2 text-sm text-primary sm:col-span-2">
              <input
                type="checkbox"
                checked={edit.active}
                onChange={(e) => setEdit({ ...edit, active: e.target.checked })}
              />{" "}
              Active (offered when planning legs)
            </label>
            {edit.id && (
              <div className="rounded-xl bg-gray-bg/60 p-3 text-sm sm:col-span-2">
                <p className="text-xs font-medium text-muted">Last 30 days</p>
                <p className="mt-1 text-primary">
                  {st(edit).open_legs} open · {st(edit).delivered_recent} delivered ·{" "}
                  {money(st(edit).cost_recent_cents)} est. spend
                </p>
              </div>
            )}
            {formErr ? (
              <p role="alert" className="text-sm text-red-700 sm:col-span-2">
                {formErr}
              </p>
            ) : null}
          </div>
        )}
      </Drawer>
    </AdminPage>
  );
}

export function PartnerJobsClient() {
  const [tick, setTick] = useState(0);
  return (
    <AdminPage
      title="Partner jobs"
      description="Legs handed to partners: request, accept, pick up, deliver."
      actions={
        <div className="flex gap-2">
          <Link
            href="/partners"
            className="inline-flex items-center gap-2 rounded-xl border border-primary/15 bg-white px-3.5 py-2 text-sm font-medium text-primary hover:bg-gray-bg"
          >
            Partners
          </Link>
          <Button onClick={() => setTick((n) => n + 1)}>Refresh</Button>
        </div>
      }
    >
      <PartnerJobsPanel tick={tick} console />
    </AdminPage>
  );
}
