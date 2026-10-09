"use client";

import { startTransition, useCallback, useEffect, useOptimistic, useState } from "react";
import { Button } from "@/components/crm/primitives";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { ordersApi, type OrderDetail } from "@/lib/orders";

type Snapshot = Awaited<ReturnType<typeof ordersApi.driverOps>>;
type ParcelRow = Snapshot["parcels"][number];

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
  const [proofUrl, setProofUrl] = useState("");
  const [stopKind, setStopKind] = useState("delivery");
  const [stopAddress, setStopAddress] = useState("");
  const [stopDollars, setStopDollars] = useState("");
  const [link, setLink] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [announce, setAnnounce] = useState<string | null>(null);

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

  const baseParcels = snapshot?.parcels ?? [];
  const [parcels, markParcelStatus] = useOptimistic(
    baseParcels,
    (current: ParcelRow[], update: { parcelId: string; status: string }) =>
      current.map((parcel) =>
        String(parcel.id ?? "") === update.parcelId ? { ...parcel, status: update.status } : parcel
      )
  );

  if (profile?.role !== "super_admin") return null;

  async function run(action: string) {
    let reason: string | undefined;
    if (action === "complete_delivery_without_proof") {
      // Override of the proof-of-delivery and on-shift gates — always audited with a reason.
      const answer = window.prompt(
        "Finish this delivery without proof? This is recorded in the audit log.\nReason (required):"
      );
      if (answer === null) return;
      reason = answer.trim();
      if (reason.length < 5) {
        setError("Give a reason (at least 5 characters) to finish without proof.");
        return;
      }
    }
    setBusy(action);
    setError(null);
    try {
      const token = await getApiToken();
      if (!token) throw new Error("Sign in again");
      await ordersApi.runDriverOp(token, detail.order_id, action, reason);
      await load();
      onRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Driver step failed");
    } finally {
      setBusy(null);
    }
  }

  function setStatus(parcelId: string, status: string, trackingSuffix?: string) {
    setError(null);
    startTransition(async () => {
      markParcelStatus({ parcelId, status });
      setAnnounce(`Parcel status updated to ${STATUS_LABEL[status] ?? status}`);
      setBusy(parcelId);
      try {
        const token = await getApiToken();
        if (!token) throw new Error("Sign in again");
        await ordersApi.setParcelStatus(token, detail.order_id, parcelId, status, trackingSuffix);
        await load();
        onRefresh?.();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not update parcel status");
        setAnnounce("Could not update parcel status");
        await load();
      } finally {
        setBusy(null);
      }
    });
  }

  async function addProof() {
    setBusy("proof");
    setError(null);
    try {
      const token = await getApiToken();
      if (!token) throw new Error("Sign in again");
      await ordersApi.addProof(token, detail.order_id, proofUrl.trim());
      setProofUrl("");
      await load();
      onRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add proof");
    } finally {
      setBusy(null);
    }
  }

  async function addStop() {
    setBusy("extra");
    setError(null);
    setLink(null);
    try {
      const token = await getApiToken();
      if (!token) throw new Error("Sign in again");
      const cents = Math.round(Number(stopDollars) * 100);
      const result = await ordersApi.addExtraStop(token, detail.order_id, {
        kind: stopKind,
        formatted: stopAddress.trim(),
        amount_cents: cents,
      });
      setLink(result.checkout_url);
      setStopAddress("");
      setStopDollars("");
      await load();
      onRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add the stop");
    } finally {
      setBusy(null);
    }
  }

  async function resend(leg: string) {
    setBusy(`resend-${leg}`);
    setError(null);
    try {
      const token = await getApiToken();
      if (!token) throw new Error("Sign in again");
      const result = await ordersApi.resendExtraStop(token, detail.order_id, leg);
      setLink(result.checkout_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not resend the link");
    } finally {
      setBusy(null);
    }
  }

  const actions = snapshot?.actions ?? [];
  const statuses = snapshot?.parcel_statuses ?? [];

  return (
    <section className="mt-4 rounded-2xl border border-primary/15 bg-white p-4">
      {announce ? (
        <p className="sr-only" role="status" aria-live="polite">
          {announce}
        </p>
      ) : null}
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
                  onChange={(event) =>
                    void setStatus(id, event.target.value, String(parcel.tracking_suffix ?? ""))
                  }
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
      <div className="mt-4 space-y-2">
        <p className="text-xs font-bold text-muted">Proof photo later</p>
        <div className="flex flex-wrap gap-2">
          <input
            className="min-w-64 flex-1 rounded-lg border border-primary/15 px-2 py-1 text-sm"
            placeholder="https://… proof image URL"
            value={proofUrl}
            onChange={(event) => setProofUrl(event.target.value)}
          />
          <Button
            type="button"
            className="px-2 py-1 text-xs"
            disabled={Boolean(busy)}
            onClick={() => void addProof()}
          >
            {busy === "proof" ? "Saving…" : "Add proof photo"}
          </Button>
        </div>
      </div>
      <div className="mt-4 space-y-2">
        <p className="text-xs font-bold text-muted">Additional pickup or delivery</p>
        <div className="flex flex-wrap gap-2">
          <select
            className="rounded-lg border border-primary/15 px-2 py-1 text-sm"
            value={stopKind}
            onChange={(event) => setStopKind(event.target.value)}
          >
            <option value="pickup">Pickup</option>
            <option value="delivery">Delivery</option>
          </select>
          <input
            className="min-w-64 flex-1 rounded-lg border border-primary/15 px-2 py-1 text-sm"
            placeholder="Address"
            value={stopAddress}
            onChange={(event) => setStopAddress(event.target.value)}
          />
          <input
            className="w-28 rounded-lg border border-primary/15 px-2 py-1 text-sm"
            placeholder="Amount CAD"
            value={stopDollars}
            onChange={(event) => setStopDollars(event.target.value)}
          />
          <Button
            type="button"
            className="px-2 py-1 text-xs"
            disabled={Boolean(busy)}
            onClick={() => void addStop()}
          >
            {busy === "extra" ? "Sending…" : "Add stop and send link"}
          </Button>
        </div>
        {link ? (
          <p className="text-xs">
            Customer payment link:{" "}
            <a className="text-secondary underline" href={link}>
              {link}
            </a>
          </p>
        ) : null}
        {(snapshot?.extra_stops ?? []).map((stop) => (
          <p
            key={String(stop.leg)}
            className="flex flex-wrap items-center gap-2 text-xs text-muted"
          >
            <span>
              {String(stop.kind)} · {String(stop.formatted)} · {String(stop.status)}
            </span>
            {stop.status === "pending" && stop.leg ? (
              <button
                type="button"
                className="font-semibold text-secondary"
                disabled={Boolean(busy)}
                onClick={() => void resend(String(stop.leg))}
              >
                Resend link
              </button>
            ) : null}
          </p>
        ))}
      </div>
    </section>
  );
}
