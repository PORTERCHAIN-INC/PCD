"use client";

import { OrdersTable } from "@/components/orders/OrdersTable";
import { OrdersToolbar } from "@/components/orders/OrdersToolbar";
import { StatCard } from "@/components/portal/StatCard";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { useMerchantRealtime } from "@/hooks/useMerchantRealtime";
import {
  exportOrdersCsv,
  ordersApi,
  printOrderLabels,
  type OrderFilters,
  type OrderRow,
  type OrdersDashboard,
} from "@/lib/orders";
import { formatCents } from "@/lib/utils";
import { useCallback, useEffect, useState } from "react";

export default function OrdersPage() {
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const [rows, setRows] = useState<OrderRow[]>([]);
  const [dashboard, setDashboard] = useState<OrdersDashboard | null>(null);
  const [filters, setFilters] = useState<OrderFilters>({});
  const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!isSignedIn) return;
    const token = await getApiToken();
    const [list, dash] = await Promise.all([
      ordersApi.list(token, orgId, filters),
      ordersApi.dashboard(token, orgId),
    ]);
    setRows(list);
    setDashboard(dash);
    setError(null);
  }, [filters, getApiToken, isSignedIn, orgId]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    setLoading(true);
    void load()
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load orders"))
      .finally(() => setLoading(false));
  }, [isLoaded, isSignedIn, load]);

  useMerchantRealtime(isLoaded && isSignedIn, orgId, getApiToken, () => {
    void load();
  });

  const selectedRows = rows.filter((r) => selected.includes(r.order_id));

  async function runBulk(action: string) {
    if (!selected.length) return;
    const token = await getApiToken();
    await ordersApi.bulk(token, selected, action, orgId);
    setSelected([]);
    await load();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">Orders</h1>
        <p className="text-sm text-muted">
          Enterprise order platform — lifecycle, tracking, billing, and dispatch
        </p>
      </div>

      {dashboard && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
          <StatCard label="Today" value={String(dashboard.orders_today)} />
          <StatCard label="In progress" value={String(dashboard.orders_in_progress)} />
          <StatCard label="Waiting dispatch" value={String(dashboard.waiting_dispatch)} />
          <StatCard label="Delivered" value={String(dashboard.delivered)} />
          <StatCard label="Claims" value={String(dashboard.claims)} />
          <StatCard label="Support" value={String(dashboard.open_support_tickets)} />
          <StatCard label="Revenue today" value={formatCents(dashboard.revenue_today_cents)} />
          <StatCard label="Avg delivery" value={`${dashboard.avg_delivery_hours}h`} />
        </div>
      )}

      <div className="rounded-2xl border border-primary/10 bg-white p-4">
        <OrdersToolbar
          filters={filters}
          onChange={setFilters}
          onSearch={() => void load()}
          selectedCount={selected.length}
          onBulkCancel={() => {
            if (!window.confirm("Cancel selected orders?")) return;
            void runBulk("cancel");
          }}
          onBulkDuplicate={() => void runBulk("duplicate")}
          onExport={() => exportOrdersCsv(selected.length ? selectedRows : rows)}
          onPrintLabels={() => printOrderLabels(selected.length ? selectedRows : rows.slice(0, 20))}
          onPrintManifest={() => window.print()}
        />

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        {loading ? (
          <p className="mt-6 text-center text-sm text-muted">Loading orders…</p>
        ) : (
          <div className="mt-4">
            <OrdersTable rows={rows} selected={selected} onSelect={setSelected} />
          </div>
        )}
      </div>
    </div>
  );
}
