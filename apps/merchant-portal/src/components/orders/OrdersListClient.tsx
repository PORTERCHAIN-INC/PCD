"use client";

import { OrdersTable } from "@/components/orders/OrdersTable";
import { OrdersToolbar } from "@/components/orders/OrdersToolbar";
import { ListPager } from "@/components/portal/ListPager";
import { StatCard } from "@/components/portal/StatCard";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { useMerchantRealtime } from "@/hooks/useMerchantRealtime";
import {
  exportOrdersCsv,
  downloadMerchantFile,
  ORDER_PAGE_SIZE,
  ordersApi,
  type BulkActionResult,
  type OrderFilters,
} from "@/lib/orders";
import { formatCents } from "@/lib/utils";
import { hasMerchantModule } from "@/lib/merchant-nav";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";

export default function OrdersListClient() {
  const { getApiToken, orgId, isLoaded, isSignedIn, modules } = useMerchantAuth();
  const qc = useQueryClient();
  const [offset, setOffset] = useState(0);
  const [filters, setFilters] = useState<OrderFilters>({});
  const [selected, setSelected] = useState<string[]>([]);
  const [actionError, setActionError] = useState<string | null>(null);
  const [printBusy, setPrintBusy] = useState(false);
  const [bulkNote, setBulkNote] = useState<string | null>(null);
  const [bulkFailures, setBulkFailures] = useState<BulkActionResult[]>([]);

  const enabled = Boolean(isLoaded && isSignedIn && orgId);

  const listQuery = useQuery({
    queryKey: ["merchant-orders", orgId, filters, offset],
    enabled,
    queryFn: async () => {
      const token = await getApiToken();
      return ordersApi.list(token, orgId, { ...filters, limit: ORDER_PAGE_SIZE, offset });
    },
  });

  const dashQuery = useQuery({
    queryKey: ["merchant-orders-dashboard", orgId],
    enabled,
    staleTime: 120_000,
    queryFn: async () => ordersApi.dashboard(await getApiToken(), orgId),
  });

  const refreshLists = useCallback(() => {
    void qc.invalidateQueries({ queryKey: ["merchant-orders", orgId] });
  }, [orgId, qc]);

  useMerchantRealtime(enabled, orgId, getApiToken, refreshLists);

  const rows = listQuery.data?.items ?? [];
  const total = listQuery.data?.total ?? 0;
  const dashboard = dashQuery.data ?? null;
  const error =
    actionError ||
    (listQuery.error instanceof Error
      ? listQuery.error.message
      : listQuery.error
        ? String(listQuery.error)
        : null);
  const loading = listQuery.isLoading;

  function changeFilters(next: OrderFilters) {
    setOffset(0);
    setFilters(next);
  }

  const selectedRows = rows.filter((r) => selected.includes(r.order_id));

  async function runBulk(action: string) {
    if (!selected.length) return;
    const token = await getApiToken();
    const result = await ordersApi.bulk(token, selected, action, orgId);
    const failures = result.results.filter((row) => !row.ok);
    const okCount = result.ok_count ?? result.results.length - failures.length;
    const verb = action === "cancel" ? "cancelled" : "duplicated";
    setBulkFailures(failures);
    if (failures.length && okCount) {
      setBulkNote(`${okCount} ${verb}. ${failures.length} could not be ${verb}.`);
    } else if (failures.length) {
      setBulkNote(`None of the selected orders could be ${verb}.`);
    } else {
      setBulkNote(`${okCount} ${verb}.`);
    }
    setSelected([]);
    refreshLists();
    void qc.invalidateQueries({ queryKey: ["merchant-orders-dashboard", orgId] });
  }

  async function downloadPrint(kind: "preview" | "list" | "labels" | "manifest") {
    const targets = selected.length ? selectedRows : rows.slice(0, 20);
    if (!targets.length) {
      setActionError("Select at least one order to print.");
      return;
    }
    setPrintBusy(true);
    try {
      const token = await getApiToken();
      if (kind === "preview") {
        const row = targets[0];
        await downloadMerchantFile(
          token,
          ordersApi.printPreviewPath(row.order_id),
          `print-preview-${row.tracking_number}.pdf`,
          orgId
        );
      } else if (kind === "labels") {
        if (targets.length === 1) {
          const row = targets[0];
          await downloadMerchantFile(
            token,
            ordersApi.labelsPdfPath(row.order_id),
            `labels-${row.tracking_number}.pdf`,
            orgId
          );
        } else {
          await downloadMerchantFile(token, ordersApi.labelsBulkPath(), "labels-bulk.pdf", orgId, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ order_ids: targets.map((r) => r.order_id) }),
          });
        }
      } else if (kind === "manifest") {
        await downloadMerchantFile(
          token,
          ordersApi.pickupManifestPath(targets.map((r) => r.order_id)),
          "pickup-manifest.pdf",
          orgId
        );
      } else {
        await downloadMerchantFile(
          token,
          ordersApi.pickupListPath(targets.map((r) => r.order_id)),
          "pickup-list.pdf",
          orgId
        );
      }
      setActionError(null);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Could not download print file");
    } finally {
      setPrintBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">Orders</h1>
        <p className="text-sm text-muted">Search, filter, and open Order 360</p>
      </div>

      {dashboard && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
          <StatCard label="Today" value={String(dashboard.orders_today)} />
          <StatCard label="In progress" value={String(dashboard.orders_in_progress)} />
          <StatCard label="Waiting dispatch" value={String(dashboard.waiting_dispatch)} />
          <StatCard label="Delivered" value={String(dashboard.delivered)} />
          <StatCard label="Claims" value={String(dashboard.claims)} />
          <StatCard label="Support" value={String(dashboard.open_support_tickets)} />
          {hasMerchantModule(modules, "billing") ? (
            <StatCard label="Revenue today" value={formatCents(dashboard.revenue_today_cents)} />
          ) : null}
          <StatCard label="Avg delivery" value={`${dashboard.avg_delivery_hours}h`} />
        </div>
      )}

      <div className="rounded-2xl border border-primary/10 bg-white p-4">
        <OrdersToolbar
          filters={filters}
          onChange={changeFilters}
          onSearch={() => void listQuery.refetch()}
          selectedCount={selected.length}
          onBulkCancel={() => {
            const selectedRowsLocal = rows.filter((r) => selected.includes(r.order_id));
            const hasLive = selectedRowsLocal.some((r) => !r.is_sandbox);
            const hasTest = selectedRowsLocal.some((r) => r.is_sandbox);
            if (hasLive && hasTest) {
              if (
                !window.confirm("Selection mixes Live and Test orders. Cancel both environments?")
              ) {
                return;
              }
            }
            if (
              !window.confirm(
                "Cancel the selected orders? You can cancel until the driver is on the way to pickup. We'll show you if any cannot be cancelled."
              )
            ) {
              return;
            }
            void runBulk("cancel").catch((e) =>
              setActionError(e instanceof Error ? e.message : "Could not cancel orders")
            );
          }}
          onBulkDuplicate={() => {
            const selectedRowsLocal = rows.filter((r) => selected.includes(r.order_id));
            const hasLive = selectedRowsLocal.some((r) => !r.is_sandbox);
            const hasTest = selectedRowsLocal.some((r) => r.is_sandbox);
            if (hasLive && hasTest) {
              if (
                !window.confirm(
                  "Selection mixes Live and Test. Duplicates inherit each order’s environment (no promote-to-live)."
                )
              ) {
                return;
              }
            }
            void runBulk("duplicate").catch((e) =>
              setActionError(e instanceof Error ? e.message : "Could not duplicate orders")
            );
          }}
          onExport={() => exportOrdersCsv(selected.length ? selectedRows : rows)}
          onPrintPreview={() => void downloadPrint("preview")}
          onPrintLabels={() => {
            const selectedRowsLocal = rows.filter((r) => selected.includes(r.order_id));
            if (selectedRowsLocal.some((r) => r.is_sandbox)) {
              if (
                !window.confirm(
                  "Selection includes Test orders. Labels will carry a TEST watermark. Continue?"
                )
              ) {
                return;
              }
            }
            void downloadPrint("labels");
          }}
          onPrintPickupList={() => void downloadPrint("list")}
          onPrintManifest={() => void downloadPrint("manifest")}
          printBusy={printBusy}
        />

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        {bulkNote && (
          <div className="mt-3 rounded-xl border border-primary/10 bg-gray-bg px-3 py-2 text-sm">
            <p className="font-medium text-primary">{bulkNote}</p>
            {bulkFailures.length > 0 && (
              <ul className="mt-2 space-y-1 text-muted">
                {bulkFailures.map((row) => (
                  <li key={row.order_id}>
                    {row.tracking_number || row.order_id} — {row.message}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        {loading ? (
          <p className="mt-6 text-center text-sm text-muted">Loading orders…</p>
        ) : (
          <div className="mt-4">
            <OrdersTable rows={rows} selected={selected} onSelect={setSelected} />
            <ListPager
              total={total}
              limit={ORDER_PAGE_SIZE}
              offset={offset}
              onPage={(next) => {
                setSelected([]);
                setOffset(next);
              }}
              note="CSV export and print use this page, not every matching order."
            />
          </div>
        )}
      </div>
    </div>
  );
}
