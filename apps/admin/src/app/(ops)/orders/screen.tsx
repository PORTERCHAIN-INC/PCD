"use client";

import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Package, Plus, RefreshCw } from "lucide-react";
import { cn, formatCents } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import OrdersGrid from "@/components/orders/OrdersGrid";
import dynamic from "next/dynamic";
import { ListPager } from "@/components/crm/ListPager";
import { Button } from "@/components/crm/primitives";
import { ORDER_PAGE_SIZE, ORDER_STATES, ordersApi, type OrderFilters } from "@/lib/orders";
import { boardQuery, boardSummary, type OrderPeriod, type OrderQueue } from "@/lib/orderBoard";
import AdminPage from "@/components/layout/AdminPage";
import OpsPageHero from "@/components/layout/OpsPageHero";
import { PageSkeleton } from "@porterchain/ui/loading";

const OrderBuilderModal = dynamic(
  () => import("@/components/orders/OrderBuilderModal").then((m) => m.OrderBuilderModal),
  { ssr: false, loading: () => <PageSkeleton rows={3} /> }
);

export default function OrdersPage() {
  const router = useRouter();
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const qc = useQueryClient();
  const [filters, setFilters] = useState<OrderFilters>({});
  const [period, setPeriod] = useState<OrderPeriod>("today");
  const [queue, setQueue] = useState<OrderQueue | "">("needs_decision");
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<string[]>([]);
  const [builderOpen, setBuilderOpen] = useState(false);
  const [showMoreMetrics, setShowMoreMetrics] = useState(false);
  const board = useMemo(
    () => boardQuery(period, queue, customFrom, customTo, filters.state),
    [period, queue, customFrom, customTo, filters.state]
  );
  const filterKey = JSON.stringify({ ...filters, ...board, period });

  const {
    data: page,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["orders", filterKey, offset],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => {
      const token = await getApiToken();
      return ordersApi.list(token, { ...filters, ...board, limit: ORDER_PAGE_SIZE, offset });
    },
  });
  const rows = page?.items ?? [];
  const total = page?.total ?? 0;

  function changeFilters(next: OrderFilters | ((current: OrderFilters) => OrderFilters)) {
    setOffset(0);
    setSelected([]);
    setFilters(next);
  }

  const { data: dashboard } = useQuery({
    queryKey: ["orders-dashboard"],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => {
      const token = await getApiToken();
      return ordersApi.dashboard(token);
    },
  });

  return (
    <AdminPage>
      <OpsPageHero
        icon={Package}
        title="Orders"
        description={boardSummary(period, queue, filters.state, customFrom, customTo)}
        actions={
          <>
            <Button variant="outline" onClick={() => void refetch()}>
              <RefreshCw className="h-4 w-4" /> Refresh
            </Button>
            <Button onClick={() => setBuilderOpen(true)}>
              <Plus className="h-4 w-4" /> New order
            </Button>
          </>
        }
      >
        <div className="flex flex-wrap gap-1.5">
          {(
            [
              ["today", "Today"],
              ["yesterday", "Yesterday"],
              ["last7", "Last 7 days"],
              ["last_month", "Last month"],
              ["all", "Any time"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => {
                setOffset(0);
                setSelected([]);
                setPeriod(id);
              }}
              className={cn(
                "rounded-full px-3 py-1 text-xs font-medium transition-colors",
                period === id
                  ? "bg-secondary text-white"
                  : "bg-white text-primary/70 ring-1 ring-primary/10 hover:bg-gray-bg"
              )}
            >
              {label}
            </button>
          ))}
          <button
            type="button"
            onClick={() => {
              setOffset(0);
              setSelected([]);
              setPeriod("custom");
            }}
            className={cn(
              "rounded-full px-3 py-1 text-xs font-medium transition-colors",
              period === "custom"
                ? "bg-secondary text-white"
                : "bg-white text-primary/70 ring-1 ring-primary/10 hover:bg-gray-bg"
            )}
          >
            Custom
          </button>
        </div>
      </OpsPageHero>

      {dashboard && (
        <div className="space-y-2">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            <Kpi
              label="Today"
              value={dashboard.orders_today}
              onClick={() => {
                setPeriod("today");
                setQueue("");
                changeFilters((f) => ({ ...f, state: undefined }));
              }}
            />
            <Kpi
              label="In progress"
              value={dashboard.orders_in_progress}
              onClick={() => {
                setPeriod("all");
                setQueue("on_the_road");
                changeFilters((f) => ({ ...f, state: undefined }));
              }}
            />
            <Kpi
              label="Waiting dispatch"
              value={dashboard.waiting_dispatch}
              onClick={() => {
                setPeriod("all");
                setQueue("needs_decision");
                changeFilters((f) => ({ ...f, state: undefined }));
              }}
            />
            <Kpi
              label="Failed"
              value={dashboard.failed}
              alert={dashboard.failed > 0}
              onClick={() => {
                setPeriod("all");
                setQueue("");
                changeFilters((f) => ({ ...f, state: "FAILED" }));
              }}
            />
            <Kpi label="Revenue today" value={formatCents(dashboard.revenue_today_cents)} />
            <Kpi label="Avg SLA" value={`${dashboard.avg_sla_percent}%`} />
          </div>
          <button
            type="button"
            className="text-xs font-medium text-secondary hover:underline"
            onClick={() => setShowMoreMetrics((v) => !v)}
          >
            {showMoreMetrics ? "Hide metrics" : "More metrics"}
          </button>
          {showMoreMetrics ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
              <Kpi label="Assigned" value={dashboard.assigned} />
              <Kpi label="Picked up" value={dashboard.picked_up} />
              <Kpi label="Delivered" value={dashboard.delivered} />
              <Kpi label="Returned" value={dashboard.returned} />
              <Kpi label="Claims" value={dashboard.claims} />
              <Kpi label="Avg delivery" value={`${dashboard.avg_delivery_hours}h`} />
            </div>
          ) : null}
        </div>
      )}

      <div className="rounded-2xl border border-primary/10 bg-white p-4">
        <div className="mb-4 flex flex-wrap gap-2">
          <input
            type="search"
            placeholder="Order #, tracking, booking, email…"
            value={filters.search ?? ""}
            onChange={(e) => changeFilters((f) => ({ ...f, search: e.target.value || undefined }))}
            className="min-w-[200px] flex-1 rounded-xl border border-primary/10 px-3 py-2 text-sm"
          />
          {period === "custom" ? (
            <>
              <input
                type="date"
                aria-label="From"
                value={customFrom}
                onChange={(e) => {
                  setOffset(0);
                  setSelected([]);
                  setCustomFrom(e.target.value);
                }}
                className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
              />
              <input
                type="date"
                aria-label="To"
                value={customTo}
                onChange={(e) => {
                  setOffset(0);
                  setSelected([]);
                  setCustomTo(e.target.value);
                }}
                className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
              />
            </>
          ) : null}
          <select
            value={filters.state ? `state:${filters.state}` : `queue:${queue}`}
            onChange={(e) => {
              const value = e.target.value;
              if (value.startsWith("state:")) {
                setQueue("");
                changeFilters((f) => ({ ...f, state: value.slice("state:".length) }));
                return;
              }
              setQueue((value.slice("queue:".length) || "") as OrderQueue | "");
              changeFilters((f) => ({ ...f, state: undefined }));
            }}
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <optgroup label="Work">
              <option value="queue:needs_decision">Needs a decision</option>
              <option value="queue:on_the_road">On the road</option>
              <option value="queue:open">All open</option>
              <option value="queue:done">Done</option>
              <option value="queue:">Any status</option>
            </optgroup>
            <optgroup label="One status">
              {ORDER_STATES.map((s) => (
                <option key={s} value={`state:${s}`}>
                  {s.replace(/_/g, " ")}
                </option>
              ))}
            </optgroup>
          </select>
          <select
            value={filters.payment_status ?? ""}
            onChange={(e) =>
              changeFilters((f) => ({ ...f, payment_status: e.target.value || undefined }))
            }
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">Payment</option>
            <option value="SUCCEEDED">Succeeded</option>
            <option value="PENDING">Pending</option>
            <option value="FAILED">Failed</option>
          </select>
          <select
            value={filters.priority ?? ""}
            onChange={(e) =>
              changeFilters((f) => ({ ...f, priority: e.target.value || undefined }))
            }
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">Priority</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
          </select>
          <input
            type="text"
            placeholder="City"
            value={filters.city ?? ""}
            onChange={(e) => changeFilters((f) => ({ ...f, city: e.target.value || undefined }))}
            className="w-28 rounded-xl border border-primary/10 px-3 py-2 text-sm"
          />
        </div>

        {selected.length > 0 && (
          <div className="mb-3 flex gap-2 rounded-xl bg-secondary/5 px-3 py-2">
            <span className="text-sm font-medium">{selected.length} selected</span>
            <Button
              variant="outline"
              onClick={async () => {
                if (!confirm("Cancel selected orders?")) return;
                const token = await getApiToken();
                await ordersApi.bulk(token, selected, "cancel");
                setSelected([]);
                await qc.invalidateQueries({ queryKey: ["orders"] });
                void refetch();
              }}
            >
              Bulk cancel
            </Button>
          </div>
        )}

        <OrdersGrid rows={rows} selected={selected} onSelect={setSelected} loading={isLoading} />
        <ListPager
          total={total}
          limit={ORDER_PAGE_SIZE}
          offset={offset}
          onPage={(next) => {
            setSelected([]);
            setOffset(next);
          }}
          note="CSV export is this page, not every matching order."
        />
      </div>

      <OrderBuilderModal
        open={builderOpen}
        onClose={() => setBuilderOpen(false)}
        onCreated={(orderId) => {
          setBuilderOpen(false);
          void qc.invalidateQueries({ queryKey: ["orders"] });
          void qc.invalidateQueries({ queryKey: ["orders-dashboard"] });
          router.push(`/orders/${orderId}`);
        }}
      />
    </AdminPage>
  );
}

function Kpi({
  label,
  value,
  alert,
  onClick,
}: {
  label: string;
  value: string | number;
  alert?: boolean;
  onClick?: () => void;
}) {
  const className = cn(
    "rounded-xl border border-primary/10 bg-white px-3 py-2 text-left shadow-sm",
    alert && "border-amber-200 bg-amber-50",
    onClick && "hover:border-primary/30"
  );
  if (!onClick) {
    return (
      <div className={className}>
        <p className="text-xs text-muted">{label}</p>
        <p className="text-lg font-bold text-primary">{value}</p>
      </div>
    );
  }
  return (
    <button type="button" className={className} onClick={onClick}>
      <p className="text-xs text-muted">{label}</p>
      <p className="text-lg font-bold text-primary">{value}</p>
    </button>
  );
}
