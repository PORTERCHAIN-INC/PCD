"use client";

import { useEffect, useState } from "react";
import { PageSkeleton } from "@porterchain/ui/loading";
import { Button, Modal } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { ops, type AssignableDriver } from "@/lib/operations";
import { ordersApi } from "@/lib/orders";

type Props = {
  open: boolean;
  orderIds: string[];
  /** How many of the selected orders are already picked up (delivery leg). */
  deliveryLegCount?: number;
  onClose: () => void;
  onDone?: (summary: {
    assigned: number;
    failed: Array<{ order_id: string; status: string }>;
  }) => void;
};

/** Assign one driver to many orders: pickup for unassigned ones, delivery leg for picked-up ones. */
export function BulkAssignDriverModal({
  open,
  orderIds,
  deliveryLegCount = 0,
  onClose,
  onDone,
}: Props) {
  const { getApiToken } = useAdminAuth();
  const [drivers, setDrivers] = useState<AssignableDriver[]>([]);
  const [selected, setSelected] = useState("");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setSelected("");
    void (async () => {
      try {
        const rows = await ops.assignableDrivers(await getApiToken());
        if (!cancelled) setDrivers(rows);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Could not load drivers");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, getApiToken]);

  async function confirm() {
    if (!selected || orderIds.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      const res = await ordersApi.bulk(await getApiToken(), orderIds, "assign", {
        driver_id: selected,
      });
      const failed = res.results.filter((r) => r.status !== "assigned");
      onDone?.({ assigned: res.results.length - failed.length, failed });
      if (failed.length) {
        setError(
          `${failed.length} not assigned: ${failed.map((f) => f.status.replace(/^error:/, "")).join("; ")}`
        );
      } else {
        onClose();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Bulk assign failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Assign driver to ${orderIds.length} order${orderIds.length === 1 ? "" : "s"}`}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button onClick={() => void confirm()} disabled={!selected || busy || loading}>
            {busy ? "Assigning…" : "Assign"}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        {deliveryLegCount > 0 && (
          <p
            className="rounded-xl bg-secondary/5 px-3 py-2 text-xs text-muted"
            data-testid="bulk-delivery-note"
          >
            {deliveryLegCount} already picked up — the new driver takes the delivery leg; those
            orders keep their status and the previous driver&apos;s job is removed.
          </p>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {loading ? (
          <PageSkeleton rows={2} />
        ) : drivers.length === 0 ? (
          <p className="text-sm text-muted">No assignable drivers found.</p>
        ) : (
          <ul className="max-h-72 space-y-2 overflow-y-auto">
            {drivers.map((d) => (
              <li key={d.id}>
                <button
                  type="button"
                  onClick={() => setSelected(d.id)}
                  className={`flex w-full justify-between rounded-xl border px-3 py-2.5 text-left ${
                    selected === d.id
                      ? "border-secondary bg-secondary/5"
                      : "border-primary/10 hover:bg-gray-bg"
                  }`}
                >
                  <span className="text-sm font-semibold text-primary">{d.name}</span>
                  <span className="text-xs text-muted">
                    {d.is_online ? "Online" : "Offline"}
                    {d.active_orders != null ? ` · ${d.active_orders} active` : ""}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Modal>
  );
}
