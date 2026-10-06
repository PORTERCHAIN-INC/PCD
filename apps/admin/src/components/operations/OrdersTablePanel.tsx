"use client";

import { useEffect, useMemo, useState } from "react";
import { Bookmark, Search, Trash2 } from "lucide-react";
import { useApiData } from "@/hooks/useApiData";
import { BOARD_LABELS, ops, SLA_TONE, type OpsOrder } from "@/lib/operations";
import { Badge, Button, EmptyState, SectionCard } from "@/components/crm/primitives";
import { dateTime, titleCase } from "@/lib/crmFormat";
import { TableSkeleton } from "@porterchain/ui/loading";

const VIEWS_KEY = "porterchain.ops.orderViews";
const DENSITY_KEY = "porterchain.ops.orderDensity";

type Density = "comfortable" | "compact";

type SavedView = {
  id: string;
  name: string;
  search: string;
  state: string;
  sla: string;
  merchant: string;
  unassignedOnly: boolean;
  highPriorityOnly: boolean;
};

type Filters = Omit<SavedView, "id" | "name">;

const EMPTY_FILTERS: Filters = {
  search: "",
  state: "",
  sla: "",
  merchant: "",
  unassignedOnly: false,
  highPriorityOnly: false,
};

function loadViews(): SavedView[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(VIEWS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as SavedView[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveViews(views: SavedView[]) {
  localStorage.setItem(VIEWS_KEY, JSON.stringify(views));
}

function SlaBadge({ sla }: { sla: string }) {
  return (
    <Badge tone={(SLA_TONE[sla] as "green" | "amber" | "red" | "slate") ?? "slate"}>
      {titleCase(sla)}
    </Badge>
  );
}

function matches(o: OpsOrder, f: Filters): boolean {
  if (f.search) {
    const q = f.search.toLowerCase();
    const hay =
      `${o.tracking_number} ${o.order_number} ${o.merchant ?? ""} ${o.driver ?? ""}`.toLowerCase();
    if (!hay.includes(q)) return false;
  }
  if (f.state && o.state !== f.state) return false;
  if (f.sla && o.sla !== f.sla) return false;
  if (f.merchant && (o.merchant ?? "") !== f.merchant) return false;
  if (f.unassignedOnly && o.driver) return false;
  if (f.highPriorityOnly && !o.high_priority) return false;
  return true;
}

export function OrdersTablePanel({
  tick,
  onOpenOrder,
}: {
  tick: number;
  onOpenOrder: (id: string) => void;
}) {
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [views, setViews] = useState<SavedView[]>([]);
  const [density, setDensity] = useState<Density>("comfortable");
  const [viewName, setViewName] = useState("");

  useEffect(() => {
    setViews(loadViews());
    const d = localStorage.getItem(DENSITY_KEY);
    if (d === "compact" || d === "comfortable") setDensity(d);
  }, []);

  const { data, loading } = useApiData(
    (t) => ops.orders(t, filters.search || undefined),
    [tick, filters.search],
    { key: "ops-orders" }
  );

  const merchants = useMemo(() => {
    const set = new Set<string>();
    for (const o of data ?? []) {
      if (o.merchant) set.add(o.merchant);
    }
    return [...set].sort();
  }, [data]);

  const states = useMemo(() => {
    const set = new Set<string>();
    for (const o of data ?? []) set.add(o.state);
    return [...set].sort();
  }, [data]);

  const rows = useMemo(() => (data ?? []).filter((o) => matches(o, filters)), [data, filters]);

  const cellPad = density === "compact" ? "px-3 py-1" : "px-4 py-2";

  const persistDensity = (d: Density) => {
    setDensity(d);
    localStorage.setItem(DENSITY_KEY, d);
  };

  const applyView = (v: SavedView) => {
    setFilters({
      search: v.search,
      state: v.state,
      sla: v.sla,
      merchant: v.merchant,
      unassignedOnly: v.unassignedOnly,
      highPriorityOnly: v.highPriorityOnly,
    });
  };

  const saveCurrentView = () => {
    const name = viewName.trim();
    if (!name) return;
    const next: SavedView = {
      id: crypto.randomUUID(),
      name,
      ...filters,
    };
    const updated = [...views.filter((v) => v.name !== name), next];
    setViews(updated);
    saveViews(updated);
    setViewName("");
  };

  const deleteView = (id: string) => {
    const updated = views.filter((v) => v.id !== id);
    setViews(updated);
    saveViews(updated);
  };

  return (
    <SectionCard
      title="Active orders"
      action={
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              value={filters.search}
              onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
              placeholder="Search tracking…"
              className="w-48 rounded-xl border border-primary/15 py-1.5 pl-9 pr-3 text-sm outline-none focus:border-secondary"
            />
          </div>
          <select
            value={density}
            onChange={(e) => persistDensity(e.target.value as Density)}
            className="rounded-xl border border-primary/15 px-2 py-1.5 text-xs outline-none"
            title="Row density"
          >
            <option value="comfortable">Comfortable</option>
            <option value="compact">Compact</option>
          </select>
        </div>
      }
    >
      <div className="mb-3 flex flex-wrap items-end gap-2 border-b border-primary/5 pb-3">
        <label className="text-xs text-muted">
          State
          <select
            value={filters.state}
            onChange={(e) => setFilters((f) => ({ ...f, state: e.target.value }))}
            className="mt-0.5 block rounded-lg border border-primary/15 px-2 py-1.5 text-sm"
          >
            <option value="">All</option>
            {states.map((s) => (
              <option key={s} value={s}>
                {BOARD_LABELS[s] ?? titleCase(s)}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-muted">
          SLA
          <select
            value={filters.sla}
            onChange={(e) => setFilters((f) => ({ ...f, sla: e.target.value }))}
            className="mt-0.5 block rounded-lg border border-primary/15 px-2 py-1.5 text-sm"
          >
            <option value="">All</option>
            <option value="ok">OK</option>
            <option value="at_risk">At risk</option>
            <option value="breached">Breached</option>
          </select>
        </label>
        <label className="text-xs text-muted">
          Merchant
          <select
            value={filters.merchant}
            onChange={(e) => setFilters((f) => ({ ...f, merchant: e.target.value }))}
            className="mt-0.5 block max-w-[10rem] rounded-lg border border-primary/15 px-2 py-1.5 text-sm"
          >
            <option value="">All</option>
            {merchants.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-1.5 pb-1.5 text-xs text-muted">
          <input
            type="checkbox"
            checked={filters.unassignedOnly}
            onChange={(e) => setFilters((f) => ({ ...f, unassignedOnly: e.target.checked }))}
          />
          Unassigned
        </label>
        <label className="flex items-center gap-1.5 pb-1.5 text-xs text-muted">
          <input
            type="checkbox"
            checked={filters.highPriorityOnly}
            onChange={(e) => setFilters((f) => ({ ...f, highPriorityOnly: e.target.checked }))}
          />
          High priority
        </label>
        <Button
          variant="outline"
          className="px-2 py-1 text-xs"
          onClick={() => setFilters(EMPTY_FILTERS)}
        >
          Clear
        </Button>
        <div className="ml-auto flex items-center gap-1.5">
          <input
            value={viewName}
            onChange={(e) => setViewName(e.target.value)}
            placeholder="Save view as…"
            className="w-36 rounded-lg border border-primary/15 px-2 py-1.5 text-xs outline-none"
          />
          <Button
            className="px-2 py-1 text-xs"
            onClick={saveCurrentView}
            disabled={!viewName.trim()}
          >
            <Bookmark className="mr-1 h-3 w-3" />
            Save
          </Button>
        </div>
      </div>

      {views.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-1.5">
          {views.map((v) => (
            <span
              key={v.id}
              className="inline-flex items-center gap-1 rounded-full border border-primary/15 bg-gray-bg/50 pl-2.5 text-xs"
            >
              <button
                type="button"
                className="py-1 hover:text-secondary"
                onClick={() => applyView(v)}
              >
                {v.name}
              </button>
              <button
                type="button"
                className="rounded-full p-1 text-muted hover:bg-red-50 hover:text-red-600"
                onClick={() => deleteView(v.id)}
                title="Delete view"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      {loading && !data ? (
        <TableSkeleton rows={6} />
      ) : (
        <div className="ops-table-scroll">
          <table className={`w-full text-left ${density === "compact" ? "text-xs" : "text-sm"}`}>
            <thead className="border-b border-primary/10 bg-gray-bg/40 text-xs uppercase text-muted">
              <tr>
                <th className={cellPad}>Tracking</th>
                <th className={cellPad}>Merchant</th>
                <th className={cellPad}>Driver</th>
                <th className={cellPad}>Route</th>
                <th className={cellPad}>ETA</th>
                <th className={cellPad}>Status</th>
                <th className={cellPad}>SLA</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((o) => (
                <tr
                  key={o.id}
                  onClick={() => onOpenOrder(o.id)}
                  className="cursor-pointer border-b border-primary/5 transition-colors hover:bg-gray-bg/60"
                  title="Open Order 360"
                >
                  <td className={`${cellPad} font-mono text-xs font-semibold text-primary`}>
                    {o.tracking_number}
                    {o.high_priority && (
                      <Badge tone="red" className="ml-1">
                        High
                      </Badge>
                    )}
                  </td>
                  <td className={cellPad}>{o.merchant ?? "—"}</td>
                  <td className={cellPad}>
                    {o.driver ?? <span className="text-muted">Unassigned</span>}
                  </td>
                  <td className={`${cellPad} text-xs text-muted`}>
                    {o.pickup ?? "?"} → {o.dropoff ?? "?"}
                  </td>
                  <td className={`${cellPad} text-xs`}>{o.eta ? dateTime(o.eta) : "—"}</td>
                  <td className={cellPad}>
                    <Badge tone="sky">{titleCase(o.state)}</Badge>
                  </td>
                  <td className={cellPad}>
                    <SlaBadge sla={o.sla} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length === 0 && (
            <EmptyState
              title="No orders match filters"
              hint="Clear filters or save a broader view."
            />
          )}
          {rows.length > 0 && (
            <p className="px-4 py-2 text-xs text-muted">
              Showing {rows.length}
              {data && data.length !== rows.length ? ` of ${data.length}` : ""} active orders
            </p>
          )}
        </div>
      )}
    </SectionCard>
  );
}
