"use client";

import MagicCard from "@/components/magic/MagicCard";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { listRouteImports, type RouteListItem } from "@/lib/api";
import { formatCents } from "@/lib/booking";
import { VEHICLE_CHOICES } from "@/lib/route-module/allocateVehicle";
import { DateTimePickerSeparateField } from "@porterchain/ui/datetime-picker-separate";
import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";

type Scope = "all" | "today";

export default function RouteList({ refreshKey = 0 }: { refreshKey?: number }) {
  const { getApiToken, orgId } = useMerchantAuth();
  const [scope, setScope] = useState<Scope>("all");
  const [date, setDate] = useState("");
  const [construction, setConstruction] = useState(false);
  const [vehicle, setVehicle] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [total, setTotal] = useState(0);
  const [today, setToday] = useState(0);
  const [constructionCount, setConstructionCount] = useState(0);
  const [routes, setRoutes] = useState<RouteListItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const token = await getApiToken();
        const result = await listRouteImports(token, {
          date: scope === "today" ? todayStamp() : date ? date.slice(0, 10) : undefined,
          construction,
          vehicleClass: vehicle || undefined,
          status: status || undefined,
          search: search || undefined,
          orgId,
        });
        if (cancelled) return;
        setTotal(result.total);
        setToday(result.today);
        setConstructionCount(result.construction);
        setRoutes(result.routes);
        setError(null);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load routes");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [construction, date, getApiToken, orgId, refreshKey, scope, search, status, vehicle]);

  return (
    <section className="space-y-4">
      <div className="grid grid-cols-3 gap-2 sm:gap-3">
        <MagicCard className="min-w-0 p-3 sm:p-4">
          <p className="text-[10px] font-medium uppercase tracking-wide text-muted sm:text-xs">
            Today
          </p>
          <p className="mt-1 text-xl font-semibold tabular-nums text-primary sm:text-2xl">
            {today}
          </p>
        </MagicCard>
        <MagicCard className="min-w-0 p-3 sm:p-4">
          <p className="text-[10px] font-medium uppercase tracking-wide text-muted sm:text-xs">
            Total
          </p>
          <p className="mt-1 text-xl font-semibold tabular-nums text-primary sm:text-2xl">
            {total}
          </p>
        </MagicCard>
        <MagicCard className="min-w-0 p-3 sm:p-4">
          <p className="text-[10px] font-medium uppercase leading-tight tracking-wide text-muted sm:text-xs">
            Construction
          </p>
          <p className="mt-1 text-xl font-semibold tabular-nums text-primary sm:text-2xl">
            {constructionCount}
          </p>
        </MagicCard>
      </div>
      <MagicCard className="space-y-4 p-4" clip={false}>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-primary">Route list</h2>
            <p className="mt-1 text-xs text-muted">
              Filter by day, vehicle, status, or construction site.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <FilterChip
              active={scope === "today"}
              onClick={() => {
                setScope("today");
                setDate("");
              }}
            >
              Today ({today})
            </FilterChip>
            <FilterChip
              active={scope === "all" && !date}
              onClick={() => {
                setScope("all");
                setDate("");
              }}
            >
              All ({total})
            </FilterChip>
            <FilterChip
              active={construction}
              onClick={() => setConstruction((current) => !current)}
            >
              Construction sites ({constructionCount})
            </FilterChip>
          </div>
        </div>

        <div className="space-y-3">
          <DateTimePickerSeparateField
            value={date}
            onChange={(value) => {
              setDate(value);
              setScope("all");
            }}
            timezone="America/Toronto"
            showTimezone={false}
            hourFormat={12}
            timeInterval={60}
            dateLabel="Date"
            timeLabel="Time"
            datePlaceholder="Filter by date"
            timePlaceholder="Any time"
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-sm font-medium text-primary">
              Vehicle
              <select
                className="mt-1 w-full rounded-xl border border-primary/15 bg-white px-3 py-2.5 text-sm"
                value={vehicle}
                onChange={(event) => setVehicle(event.target.value)}
              >
                <option value="">All vehicles</option>
                {VEHICLE_CHOICES.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-medium text-primary">
              Status
              <select
                className="mt-1 w-full rounded-xl border border-primary/15 bg-white px-3 py-2.5 text-sm"
                value={status}
                onChange={(event) => setStatus(event.target.value)}
              >
                <option value="">All statuses</option>
                <option value="PREVIEW">Quoted</option>
                <option value="CONFIRMED">Confirmed</option>
                <option value="FAILED">Failed</option>
              </select>
            </label>
          </div>
        </div>
        <input
          className="w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
          placeholder="Search pickup, drop, or reference"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />

        {error ? <p className="text-sm text-red-700">{error}</p> : null}
        {routes.length === 0 ? (
          <p className="text-sm text-muted">No routes match these filters.</p>
        ) : (
          <ul className="divide-y divide-primary/10">
            {routes.map((route) => (
              <li
                key={route.job_id}
                className="flex min-w-0 flex-wrap items-center justify-between gap-3 py-3 text-sm"
              >
                <Link href={`/routes/${route.job_id}`} className="min-w-0 flex-1">
                  <p className="truncate font-medium text-primary">{route.label}</p>
                  <p className="text-muted">
                    {route.stop_count} stops ·{" "}
                    {VEHICLE_CHOICES.find((item) => item.id === route.vehicle_class)?.label ||
                      route.vehicle_class ||
                      "vehicle pending"}
                    {route.construction_site ? " · Construction site" : ""}
                    {route.internal_reference ? ` · ${route.internal_reference}` : ""}
                  </p>
                </Link>
                <div className="text-right">
                  <p className="font-medium text-primary">
                    {route.status === "PREVIEW" ? "Quoted" : route.status}
                  </p>
                  {route.amount_cents != null ? <p>{formatCents(route.amount_cents)}</p> : null}
                  {route.order_id ? (
                    <Link className="text-secondary" href={`/orders/${route.order_id}`}>
                      View order
                    </Link>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}
      </MagicCard>
    </section>
  );
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`min-h-10 rounded-full px-3 py-1.5 text-xs font-medium ${
        active ? "bg-primary text-white" : "bg-gray-bg text-primary"
      }`}
    >
      {children}
    </button>
  );
}

function todayStamp(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}
