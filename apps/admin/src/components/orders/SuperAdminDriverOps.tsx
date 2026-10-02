"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/crm/primitives";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { ordersApi, type OrderDetail } from "@/lib/orders";

type Snapshot = Awaited<ReturnType<typeof ordersApi.driverOps>>;

const STATUS_LABEL: Record<string, string> = {
  manifested: "Manifested",
  picked_up: "Picked up",
  loaded: "Loaded",
  out_for_delivery: "Out for delivery",
  delivered: "Delivered",
};

export function SuperAdminDriverOps({
  detail,
  onRefresh,
}: {
  detail: OrderDetail;
  onRefresh?: () => void;
}) {
  const { profile } = useAdminProfile();
  const { getApiToken } = useAdminAuth();
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = await getApiToken();
    if (!token) return;
    setSnapshot(await ordersApi.driverOps(token, detail.order_id));
  }, [detail.order_id, getApiToken]);

  useEffect(() => {
    if (profile?.role !== "super_admin") return;
    void load().catch((err: unknown) => {
      setError(err instanceof Error ? err.message : "Could not load driver steps");
    });
  }, [load, profile?.role, detail.state]);

  if (profile?.role !== "super_admin") return null;

  async function run(action: string) {
    setBusy(action);
    setError(null);
    try {
      const token = await getApiToken();
      if (!token) throw new Error("Sign in again");
      await ordersApi.runDriverOp(token, detail.order_id, action);
      await load();
      onRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Driver step failed");
    } finally {
      setBusy(null);
    }
  }

  async function setStatus(parcelId: string, status: string) {
    setBusy(parcelId);
    setError(null);
    try {
      const token = await getApiToken();
      if (!token) throw new Error("Sign in again");
      await ordersApi.setParcelStatus(token, detail.order_id, parcelId, status);
      await load();
      onRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update parcel status");
    } finally {
      setBusy(null);
    }
  }

  const actions = snapshot?.actions ?? [];
  const parcels = snapshot?.parcels ?? [];
  const statuses = snapshot?.parcel_statuses ?? [];

  return (
    <section className="mt-4 rounded-2xl border border-primary/15 bg-white p-4">
      <h2 className="text-sm font-bold text-primary">Driver steps</h2>
      <p className="mt-1 text-xs text-muted">
        Super admin can accept, start the route, and move the stop. Parcel status can be set here
        when a scan is not available. Weight changes stay locked after a driver is assigned.
      </p>
      {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
      {!snapshot?.driver_assigned ? (
        <p className="mt-3 text-sm text-muted">Assign a driver before these steps.</p>
      ) : (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {actions.length === 0 ? (
            <p className="text-sm text-muted">No driver step is open for this order.</p>
          ) : (
            actions.map((action) => (
              <Button
                key={action.id}
                type="button"
                className="px-2 py-1 text-xs"
                disabled={Boolean(busy)}
                onClick={() => void run(action.id)}
              >
                {busy === action.id ? "Working…" : action.label}
              </Button>
            ))
          )}
        </div>
      )}
      {parcels.length > 0 ? (
        <div className="mt-4 space-y-2">
          <p className="text-xs font-bold text-muted">Parcel status</p>
          {parcels.map((parcel) => {
            const id = String(parcel.id ?? "");
            const current = String(parcel.status ?? "manifested");
            return (
              <label key={id} className="flex flex-wrap items-center gap-2 text-sm">
                <span className="min-w-28 font-semibold">
                  {String(parcel.tracking_suffix || `Parcel ${parcel.parcel_index ?? ""}`)}
                </span>
                <select
                  className="rounded-lg border border-primary/15 px-2 py-1 text-sm"
                  value={current}
                  disabled={Boolean(busy) || !id}
                  onChange={(event) => void setStatus(id, event.target.value)}
                >
                  {statuses.map((status) => (
                    <option key={status} value={status}>
                      {STATUS_LABEL[status] ?? status}
                    </option>
                  ))}
                </select>
              </label>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
