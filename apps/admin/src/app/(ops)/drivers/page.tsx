"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  type ColumnDef,
  type VisibilityState,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import {
  ArrowUpDown,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Columns3,
  Download,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Star,
  UserCheck,
  UserPlus,
  Users,
  Wallet,
  X,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";
import { useApiData } from "@/hooks/useApiData";
import { drivers, healthTone, type DriverRow } from "@/lib/drivers";
import { Dropdown, FilterChip, ProvincePills } from "@/components/crm/filters";
import { Badge, Button, EmptyState, Spinner } from "@/components/crm/primitives";
import { money, shortDate, relativeTime, titleCase, downloadCsv, toCsv } from "@/lib/crmFormat";
import { AddDriverModal } from "@/components/drivers/AddDriverModal";

const STATUSES = ["PENDING", "APPROVED", "SUSPENDED", "REJECTED"];
const BG = ["pending", "passed", "failed"];
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
  NT: "NT",
  YT: "YT",
  NU: "NU",
};
const STATUS_TONE: Record<string, string> = {
  APPROVED: "green",
  PENDING: "amber",
  SUSPENDED: "red",
  REJECTED: "slate",
};
const VIEWS_KEY = "pc.drivers.views";

type SavedView = { name: string; visibility: VisibilityState };

export default function DriversPage() {
  const router = useRouter();
  const { getApiToken } = useAdminAuth();
  const { profile } = useAdminProfile();
  const canWrite = !new Set([
    "support",
    "support_lead",
    "sales",
    "sales_manager",
    "finance",
    "read_only",
    "developer",
    "marketing",
  ]).has((profile?.role || "").toLowerCase());
  const [version, setVersion] = useState(0);
  const { data, error } = useApiData((t) => drivers.list(t, { limit: "500" }), [version], {
    key: "drivers-list",
  });
  const { data: stats } = useApiData((t) => drivers.stats(t), [version], { key: "drivers-stats" });

  const [search, setSearch] = useState("");
  const [docsOnly, setDocsOnly] = useState(false);
  const [status, setStatus] = useState("");
  const [vehicleType, setVehicleType] = useState("");
  const [province, setProvince] = useState("");
  const [city, setCity] = useState("");
  const [bg, setBg] = useState("");
  const [health, setHealth] = useState("");
  const [rating, setRating] = useState("");
  const [sortBy, setSortBy] = useState("recent");

  const [sorting, setSorting] = useState<SortingState>([]);
  const [rowSelection, setRowSelection] = useState<Record<string, boolean>>({});
  const [visibility, setVisibility] = useState<VisibilityState>({
    created_at: false,
    weekly_earnings_cents: false,
  });
  const [chooserOpen, setChooserOpen] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const chooserRef = useRef<HTMLDivElement>(null);

  const [views, setViews] = useState<SavedView[]>([]);
  useEffect(() => {
    try {
      setViews(JSON.parse(localStorage.getItem(VIEWS_KEY) || "[]"));
    } catch {
      setViews([]);
    }
  }, []);
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (chooserRef.current && !chooserRef.current.contains(e.target as Node))
        setChooserOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const facets = useMemo(() => {
    const list = Array.isArray(data) ? data : [];
    const provMap = new Map<string, number>();
    const cityMap = new Map<string, number>();
    const vtSet = new Set<string>();
    list.forEach((r) => {
      if (r.province) provMap.set(r.province, (provMap.get(r.province) ?? 0) + 1);
      if (r.city) cityMap.set(r.city, (cityMap.get(r.city) ?? 0) + 1);
      if (r.vehicle_type) vtSet.add(r.vehicle_type);
    });
    return {
      provinces: [...provMap.entries()]
        .map(([code, count]) => ({ code, count }))
        .sort((a, b) => b.count - a.count),
      cities: [...cityMap.entries()]
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count),
      vehicleTypes: [...vtSet].sort(),
    };
  }, [data]);

  const rows = useMemo(() => {
    let r = Array.isArray(data) ? [...data] : [];
    const q = search.toLowerCase();
    if (q)
      r = r.filter((d) =>
        `${d.full_name} ${d.email} ${d.phone ?? ""} ${d.city ?? ""}`.toLowerCase().includes(q)
      );
    if (docsOnly) r = r.filter((d) => d.docs_pending_review);
    if (status) r = r.filter((d) => d.status === status);
    if (vehicleType) r = r.filter((d) => d.vehicle_type === vehicleType);
    if (province) r = r.filter((d) => d.province === province);
    if (city) r = r.filter((d) => d.city === city);
    if (bg) r = r.filter((d) => d.background_check_status === bg);
    if (rating === "4.5") r = r.filter((d) => (d.rating ?? 0) >= 4.5);
    else if (rating === "4") r = r.filter((d) => (d.rating ?? 0) >= 4);
    else if (rating === "low") r = r.filter((d) => (d.rating ?? 0) > 0 && (d.rating ?? 0) < 4);
    if (health === "hot") r = r.filter((d) => d.health_score >= 70);
    else if (health === "warm") r = r.filter((d) => d.health_score >= 40 && d.health_score < 70);
    else if (health === "risk") r = r.filter((d) => d.health_score < 40);
    if (sortBy === "health") r.sort((a, b) => b.health_score - a.health_score);
    else if (sortBy === "rating") r.sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0));
    else if (sortBy === "orders") r.sort((a, b) => b.orders_today - a.orders_today);
    else if (sortBy === "name") r.sort((a, b) => a.full_name.localeCompare(b.full_name));
    return r;
  }, [data, search, docsOnly, status, vehicleType, province, city, bg, rating, health, sortBy]);

  const activeFilters =
    [status, vehicleType, province, city, bg, rating, health].filter(Boolean).length +
    (sortBy !== "recent" ? 1 : 0);
  function clearFilters() {
    setStatus("");
    setVehicleType("");
    setProvince("");
    setCity("");
    setBg("");
    setRating("");
    setHealth("");
    setSortBy("recent");
  }

  const columns = useMemo<ColumnDef<DriverRow, unknown>[]>(
    () => [
      {
        id: "select",
        enableSorting: false,
        header: ({ table }) => (
          <input
            type="checkbox"
            checked={table.getIsAllPageRowsSelected()}
            onChange={table.getToggleAllPageRowsSelectedHandler()}
          />
        ),
        cell: ({ row }) => (
          <input
            type="checkbox"
            checked={row.getIsSelected()}
            onChange={row.getToggleSelectedHandler()}
            onClick={(e) => e.stopPropagation()}
          />
        ),
      },
      {
        accessorKey: "full_name",
        header: "Driver",
        cell: ({ row }) => (
          <div className="flex items-center gap-3">
            <span className="relative flex h-9 w-9 items-center justify-center overflow-hidden rounded-full bg-secondary/10 text-xs font-semibold text-secondary">
              {row.original.photo_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={row.original.photo_url} alt="" className="h-full w-full object-cover" />
              ) : (
                row.original.full_name
                  .split(" ")
                  .map((p) => p[0])
                  .slice(0, 2)
                  .join("")
              )}
            </span>
            <div>
              <p className="font-semibold text-primary">
                {row.original.full_name}
                {row.original.docs_pending_review ? (
                  <span className="ml-2 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-800">
                    Docs to review
                  </span>
                ) : null}
              </p>
              <p className="text-xs text-muted">{row.original.email}</p>
            </div>
          </div>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => (
          <div className="flex flex-wrap items-center gap-1">
            <Badge tone={STATUS_TONE[String(row.original.status)] ?? "slate"}>
              {titleCase(String(row.original.status))}
            </Badge>
            {row.original.medical_transport_certified && <Badge tone="sky">Medical</Badge>}
            {row.original.fleetbase_driver_id && <Badge tone="green">FB</Badge>}
          </div>
        ),
      },
      {
        accessorKey: "vehicle",
        header: "Vehicle",
        cell: ({ row }) => (
          <div>
            <p>{row.original.vehicle ?? "—"}</p>
            <p className="text-xs text-muted">{titleCase(row.original.vehicle_type ?? "")}</p>
          </div>
        ),
      },
      {
        accessorKey: "license_class",
        header: "License",
        cell: ({ getValue }) => String(getValue() ?? "—"),
      },
      {
        id: "location",
        header: "City",
        cell: ({ row }) =>
          [row.original.city, row.original.province].filter(Boolean).join(", ") || "—",
      },
      {
        accessorKey: "rating",
        header: "Rating",
        cell: ({ getValue }) => {
          const v = getValue() as number | null;
          return v ? (
            <span className="inline-flex items-center gap-1">
              <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
              {v.toFixed(1)}
            </span>
          ) : (
            <span className="text-muted">—</span>
          );
        },
      },
      {
        accessorKey: "acceptance_rate",
        header: "Accept %",
        cell: ({ getValue }) => `${getValue()}%`,
      },
      {
        accessorKey: "completion_rate",
        header: "Complete %",
        cell: ({ getValue }) => `${getValue()}%`,
      },
      {
        accessorKey: "orders_today",
        header: "Orders today",
        cell: ({ getValue }) => String(getValue() ?? 0),
      },
      {
        accessorKey: "weekly_earnings_cents",
        header: "Weekly earnings",
        cell: ({ getValue }) => money(getValue() as number),
      },
      {
        accessorKey: "outstanding_payout_cents",
        header: "Outstanding payout",
        cell: ({ getValue }) => money(getValue() as number),
      },
      {
        accessorKey: "health_score",
        header: "Health",
        cell: ({ getValue }) => {
          const v = Number(getValue());
          return (
            <div className="flex items-center gap-2">
              <div className="h-1.5 w-12 overflow-hidden rounded-full bg-gray-bg">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${v}%`,
                    background: v >= 70 ? "#16a34a" : v >= 40 ? "#f59e0b" : "#dc2626",
                  }}
                />
              </div>
              <Badge tone={healthTone(v)}>{v}</Badge>
            </div>
          );
        },
      },
      {
        accessorKey: "insurance_verified",
        header: "Insurance",
        cell: ({ getValue }) =>
          getValue() ? <Badge tone="green">Verified</Badge> : <Badge tone="amber">Pending</Badge>,
      },
      {
        accessorKey: "background_check_status",
        header: "Background",
        cell: ({ getValue }) => (
          <Badge tone={String(getValue()) === "passed" ? "green" : "amber"}>
            {titleCase(String(getValue()))}
          </Badge>
        ),
      },
      {
        accessorKey: "last_active_at",
        header: "Last active",
        cell: ({ getValue }) => relativeTime(getValue() as string),
      },
      {
        accessorKey: "created_at",
        header: "Created",
        cell: ({ getValue }) => shortDate(String(getValue())),
      },
    ],
    []
  );

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting, rowSelection, columnVisibility: visibility },
    onSortingChange: setSorting,
    onRowSelectionChange: setRowSelection,
    onColumnVisibilityChange: setVisibility,
    getRowId: (r) => r.id,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 25 } },
  });

  const selectedIds = Object.keys(rowSelection).filter((k) => rowSelection[k]);

  async function bulk(action: "approve" | "suspend") {
    setBusy(true);
    setActionError(null);
    try {
      const token = await getApiToken();
      for (const id of selectedIds) {
        if (action === "approve") await drivers.approve(token, id);
        else await drivers.suspend(token, id);
      }
      setRowSelection({});
      setVersion((v) => v + 1);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : `Bulk ${action} failed`);
    } finally {
      setBusy(false);
    }
  }

  function exportCsv() {
    const cols = table.getVisibleLeafColumns().filter((c) => c.id !== "select");
    const headers = cols.map((c) => String(c.columnDef.header ?? c.id));
    const body = table.getFilteredRowModel().rows.map((r) =>
      cols.map((c) => {
        const v = r.getValue(c.id);
        return v == null ? "" : String(v);
      })
    );
    downloadCsv(`drivers-${new Date().toISOString().slice(0, 10)}.csv`, toCsv(headers, body));
  }

  function saveView() {
    const name = prompt("Save current view as:");
    if (!name) return;
    const next = [...views.filter((v) => v.name !== name), { name, visibility }];
    setViews(next);
    localStorage.setItem(VIEWS_KEY, JSON.stringify(next));
  }

  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-primary">Driver Command Center</h1>
          <p className="text-sm text-muted">
            360° driver platform — performance, compliance, payouts, and risk. Identity-only invites
            live in{" "}
            <a
              href="/settings?section=users&tab=driver"
              className="font-medium text-secondary hover:underline"
            >
              Settings → Users → Drivers
            </a>
            .
          </p>
        </div>
        <Button onClick={() => setAddOpen(true)}>
          <UserPlus className="h-4 w-4" /> Add driver
        </Button>
      </div>

      {actionError && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {actionError}
        </p>
      )}

      {stats && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <StatTile icon={Users} label="Total drivers" value={stats.total.toLocaleString()} />
          <StatTile
            icon={UserCheck}
            label="Approved"
            value={String(stats.approved)}
            accent="text-green-600"
          />
          <StatTile
            icon={ShieldCheck}
            label="Pending"
            value={String(stats.pending)}
            accent="text-amber-600"
          />
          <StatTile
            icon={Users}
            label="Suspended"
            value={String(stats.suspended)}
            accent="text-red-600"
          />
          <StatTile
            icon={Wallet}
            label="Pending payouts"
            value={money(stats.pending_payout_cents)}
            accent="text-red-600"
          />
        </div>
      )}

      <div className="space-y-3 rounded-2xl border border-primary/10 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2 text-sm font-semibold text-primary">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-secondary/10 text-secondary">
              <SlidersHorizontal className="h-4 w-4" />
            </span>
            Filters
            {activeFilters > 0 && <Badge tone="blue">{activeFilters} active</Badge>}
            <span className="text-xs font-normal text-muted">
              · {rows.length.toLocaleString()} drivers
            </span>
          </span>
          {activeFilters > 0 && (
            <Button variant="ghost" onClick={clearFilters} className="text-xs">
              <X className="h-4 w-4" /> Clear
            </Button>
          )}
        </div>
        {facets.provinces.length > 0 && (
          <ProvincePills provinces={facets.provinces} value={province} onChange={setProvince} />
        )}
        <div className="flex flex-wrap items-center gap-2 border-t border-primary/5 pt-3">
          <Dropdown
            label="Status"
            value={status}
            onChange={setStatus}
            options={STATUSES.map((s) => ({ value: s, label: titleCase(s) }))}
          />
          <Dropdown
            label="Vehicle"
            value={vehicleType}
            onChange={setVehicleType}
            options={facets.vehicleTypes.map((v) => ({ value: v, label: titleCase(v) }))}
          />
          <Dropdown
            label="Background"
            value={bg}
            onChange={setBg}
            options={BG.map((s) => ({ value: s, label: titleCase(s) }))}
          />
          <Dropdown
            label="Rating"
            value={rating}
            onChange={setRating}
            allLabel="Any"
            options={[
              { value: "4.5", label: "4.5+" },
              { value: "4", label: "4.0+" },
              { value: "low", label: "Below 4" },
            ]}
          />
          <Dropdown
            label="Health"
            value={health}
            onChange={setHealth}
            allLabel="Any"
            options={[
              { value: "hot", label: "Healthy 70+" },
              { value: "warm", label: "Watch 40-69" },
              { value: "risk", label: "At risk <40" },
            ]}
          />
          <Dropdown
            label="Sort"
            value={sortBy === "recent" ? "" : sortBy}
            onChange={(v) => setSortBy(v || "recent")}
            allLabel="Recent"
            options={[
              { value: "health", label: "Health" },
              { value: "rating", label: "Rating" },
              { value: "orders", label: "Orders today" },
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
            {vehicleType && (
              <FilterChip
                label={`Vehicle: ${titleCase(vehicleType)}`}
                onRemove={() => setVehicleType("")}
              />
            )}
            {bg && <FilterChip label={`Background: ${titleCase(bg)}`} onRemove={() => setBg("")} />}
            {rating && <FilterChip label={`Rating: ${rating}`} onRemove={() => setRating("")} />}
            {health && <FilterChip label={`Health: ${health}`} onRemove={() => setHealth("")} />}
          </div>
        )}
      </div>

      <div className="rounded-2xl border border-primary/10 bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-primary/10 px-4 py-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search drivers…"
              className="w-64 rounded-xl border border-primary/15 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/20"
            />
          </div>
          <Button
            variant={docsOnly ? "primary" : "outline"}
            className="text-xs"
            onClick={() => setDocsOnly((v) => !v)}
          >
            Docs to review
          </Button>
          <div className="flex items-center gap-2">
            {views.length > 0 && (
              <select
                onChange={(e) => {
                  const v = views.find((x) => x.name === e.target.value);
                  if (v) setVisibility(v.visibility);
                }}
                className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
                defaultValue=""
              >
                <option value="">Saved views</option>
                {views.map((v) => (
                  <option key={v.name} value={v.name}>
                    {v.name}
                  </option>
                ))}
              </select>
            )}
            <Button variant="outline" onClick={saveView} className="text-xs">
              Save view
            </Button>
            <div className="relative" ref={chooserRef}>
              <Button
                variant="outline"
                onClick={() => setChooserOpen((o) => !o)}
                className="text-xs"
              >
                <Columns3 className="h-4 w-4" /> Columns
              </Button>
              {chooserOpen && (
                <div className="absolute right-0 z-30 mt-1 max-h-72 w-52 overflow-y-auto rounded-xl border border-primary/10 bg-white p-2 shadow-xl">
                  {table
                    .getAllLeafColumns()
                    .filter((c) => c.id !== "select")
                    .map((c) => (
                      <label
                        key={c.id}
                        className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-gray-bg"
                      >
                        <input
                          type="checkbox"
                          checked={c.getIsVisible()}
                          onChange={c.getToggleVisibilityHandler()}
                        />
                        {String(c.columnDef.header ?? c.id)}
                      </label>
                    ))}
                </div>
              )}
            </div>
            <Button variant="outline" onClick={exportCsv} className="text-xs">
              <Download className="h-4 w-4" /> Export
            </Button>
          </div>
        </div>

        {canWrite && selectedIds.length > 0 && (
          <div className="flex items-center gap-3 border-b border-primary/10 bg-secondary/5 px-4 py-2 text-sm">
            <span className="font-medium text-primary">{selectedIds.length} selected</span>
            <Button
              variant="outline"
              onClick={() => bulk("approve")}
              disabled={busy}
              className="text-xs"
            >
              <CheckCircle2 className="h-4 w-4" /> Approve
            </Button>
            <Button
              variant="outline"
              onClick={() => bulk("suspend")}
              disabled={busy}
              className="text-xs"
            >
              Suspend
            </Button>
            <button
              onClick={() => setRowSelection({})}
              className="ml-auto text-xs text-muted hover:text-primary"
            >
              Clear
            </button>
          </div>
        )}

        {!data || !Array.isArray(data) ? (
          <Spinner label="Loading drivers…" />
        ) : rows.length === 0 ? (
          <EmptyState
            title="No drivers match these filters"
            hint="Add a driver manually or wait for driver app registrations to appear here."
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-primary/10 bg-gray-bg/40">
                  {table.getHeaderGroups().map((hg) => (
                    <tr key={hg.id}>
                      {hg.headers.map((header) => {
                        const sortable =
                          header.column.getCanSort() && header.column.id !== "select";
                        return (
                          <th
                            key={header.id}
                            onClick={sortable ? header.column.getToggleSortingHandler() : undefined}
                            className={cn(
                              "whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted",
                              sortable && "cursor-pointer select-none"
                            )}
                          >
                            <span className="inline-flex items-center gap-1">
                              {flexRender(header.column.columnDef.header, header.getContext())}
                              {sortable && <ArrowUpDown className="h-3 w-3 opacity-50" />}
                            </span>
                          </th>
                        );
                      })}
                    </tr>
                  ))}
                </thead>
                <tbody>
                  {table.getRowModel().rows.map((row) => (
                    <tr
                      key={row.id}
                      onClick={() => router.push(`/drivers/${row.original.id}`)}
                      className="cursor-pointer border-b border-primary/5 last:border-0 hover:bg-secondary/5"
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="whitespace-nowrap px-4 py-3 text-primary">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between border-t border-primary/10 px-4 py-3 text-sm text-muted">
              <span>
                Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()} ·{" "}
                {table.getFilteredRowModel().rows.length} drivers
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => table.previousPage()}
                  disabled={!table.getCanPreviousPage()}
                  className="rounded-lg border border-primary/15 p-1.5 disabled:opacity-40"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  onClick={() => table.nextPage()}
                  disabled={!table.getCanNextPage()}
                  className="rounded-lg border border-primary/15 p-1.5 disabled:opacity-40"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      <AddDriverModal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onCreated={(driverId) => {
          setVersion((v) => v + 1);
          router.push(`/drivers/${driverId}`);
        }}
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
