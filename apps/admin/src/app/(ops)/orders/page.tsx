"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Plus, RefreshCw } from "lucide-react";
import { cn, formatCents } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import OrdersGrid from "@/components/orders/OrdersGrid";
import { OrderBuilderModal } from "@/components/orders/OrderBuilderModal";
import { ListPager } from "@/components/crm/ListPager";
import { Button } from "@/components/crm/primitives";
import { ORDER_PAGE_SIZE, ORDER_STATES, ordersApi, type OrderFilters } from "@/lib/orders";

export default function OrdersPage() {
  const router = useRouter();
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const qc = useQueryClient();
  const [filters, setFilters] = useState<OrderFilters>({});
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<string[]>([]);
  const [builderOpen, setBuilderOpen] = useState(false);
  const [showMoreMetrics, setShowMoreMetrics] = useState(false);
  const filterKey = JSON.stringify(filters);

  const {
    data: page,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["orders", filterKey, offset],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => {
      const token = await getApiToken();
      return ordersApi.list(token, { ...filters, limit: ORDER_PAGE_SIZE, offset });
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
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary">Orders</h1>
          <p className="text-sm text-muted">Scan active deliveries, open 360 to operate</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => void refetch()}>
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
          <Button onClick={() => setBuilderOpen(true)}>
            <Plus className="h-4 w-4" /> New order
          </Button>
        </div>
      </div>

      {dashboard && (
        <div className="space-y-2">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            <Kpi label="Today" value={dashboard.orders_today} />
            <Kpi label="In progress" value={dashboard.orders_in_progress} />
            <Kpi label="Waiting dispatch" value={dashboard.waiting_dispatch} />
            <Kpi label="Failed" value={dashboard.failed} alert={dashboard.failed > 0} />
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
          <select
            value={filters.state ?? ""}
            onChange={(e) => changeFilters((f) => ({ ...f, state: e.target.value || undefined }))}
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">All statuses</option>
            {ORDER_STATES.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ")}
              </option>
            ))}
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
    </div>
  );
}

function Kpi({ label, value, alert }: { label: string; value: string | number; alert?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-xl border border-primary/10 bg-white px-3 py-2 shadow-sm",
        alert && "border-amber-200 bg-amber-50"
      )}
    >
      <p className="text-xs text-muted">{label}</p>
      <p className="text-lg font-bold text-primary">{value}</p>
    </div>
  );
}
