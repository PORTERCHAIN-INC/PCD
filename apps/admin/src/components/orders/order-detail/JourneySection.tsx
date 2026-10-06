"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { cn, formatCents } from "@porterchain/ui/utils";
import { formatState, ordersApi, type OrderDetail } from "@/lib/orders";
import { relativeTime } from "@/lib/crmFormat";
import { Button } from "@/components/crm/primitives";
import { SectionBlock } from "@/components/orders/sections";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { EntityRows, Row } from "./shared";

export function TimelineTab({ detail }: { detail: OrderDetail }) {
  const items = [...detail.timeline];
  return (
    <ol className="relative border-l-2 border-secondary/20 pl-6">
      {items.map((e, i) => (
        <li key={i} className="relative mb-4">
          <span className="absolute -left-[25px] mt-1 h-3 w-3 rounded-full bg-secondary" />
          <p className="font-semibold text-primary">{String(e.label || e.event_type)}</p>
          {e.to_state ? (
            <p className="text-xs text-muted">
              {String(e.from_state)} → {String(e.to_state)}
            </p>
          ) : null}
          <p className="text-xs text-muted">
            {e.occurred_at ? relativeTime(String(e.occurred_at)) : ""}
          </p>
        </li>
      ))}
      {!items.length && <p className="text-sm text-muted">No timeline events</p>}
    </ol>
  );
}

export function TrackingTab({
  detail,
  tracking,
  live,
}: {
  detail: OrderDetail;
  tracking: Record<string, unknown> | null;
  live?: Record<string, unknown> | null;
}) {
  const history = (tracking?.history ?? []) as Array<Record<string, unknown>>;
  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-2 font-semibold">Current position</h3>
        <Row label="State" value={formatState(detail.state)} />
        <Row
          label="Scheduled"
          value={detail.scheduled_at ? String(detail.scheduled_at).slice(0, 16) : "—"}
        />
        {live?.driver_location ? (
          <Row label="GPS" value={JSON.stringify(live.driver_location)} mono />
        ) : (
          <p className="text-sm text-muted">
            Live GPS is the driver pin while the order is moving.
          </p>
        )}
      </div>
      {history.length > 0 && (
        <div>
          <h3 className="mb-2 font-semibold">GPS history & route</h3>
          <ol className="space-y-2">
            {history.map((h, i) => (
              <li key={i} className="rounded-lg border border-primary/10 px-3 py-2 text-xs">
                <span className="font-medium">{String(h.event_type || h.to_state)}</span>
                <span className="ml-2 text-muted">
                  {h.occurred_at ? relativeTime(String(h.occurred_at)) : ""}
                </span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

export function StopsTab({ stops }: { stops: unknown[] }) {
  if (!stops.length) return <p className="text-sm text-muted">No intermediate stops</p>;
  return (
    <div className="space-y-4">
      {stops.map((stop, i) => (
        <div key={i} className="rounded-xl border border-primary/10 p-3">
          <p className="mb-2 text-xs font-bold text-muted">Stop {i + 1}</p>
          {typeof stop === "object" && stop !== null ? (
            Object.entries(stop as Record<string, unknown>).map(([k, v]) => (
              <Row key={k} label={k.replace(/_/g, " ")} value={v == null ? "—" : String(v)} />
            ))
          ) : (
            <Row label="Address" value={String(stop)} />
          )}
        </div>
      ))}
    </div>
  );
}

export function AddressTab({ title, addr }: { title: string; addr: Record<string, unknown> }) {
  if (!addr || !Object.keys(addr).length)
    return <p className="text-sm text-muted">No {title.toLowerCase()} address on file</p>;
  return (
    <>
      <h3 className="mb-3 font-semibold">{title}</h3>
      {Object.entries(addr).map(([k, v]) => (
        <Row key={k} label={k.replace(/_/g, " ")} value={String(v ?? "—")} />
      ))}
    </>
  );
}

export function PackagesTab({
  detail,
  onRefresh,
}: {
  detail: OrderDetail;
  onRefresh?: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const [stops, setStops] = useState<Array<Record<string, unknown>>>(detail.stops ?? []);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setStops(detail.stops ?? []);
  }, [detail]);

  const amendable = Boolean(detail.parcel_amendable);

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const token = await getApiToken();
      await ordersApi.amendParcels(token, detail.order_id, { stops });
      onRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save parcels");
    } finally {
      setBusy(false);
    }
  }

  if (stops.length) {
    return (
      <div className="space-y-4">
        {error ? <p className="text-sm text-red-700">{error}</p> : null}
        {!amendable ? (
          <p className="text-sm text-muted">
            Parcels can be corrected only while the order is booked or ready for dispatch and no
            driver is assigned.
          </p>
        ) : null}
        {stops.map((stop, i) => {
          const packages = Array.isArray(stop.packages) ? stop.packages : [];
          return (
            <div key={i} className="rounded-xl border border-primary/10 p-3 text-sm">
              <p className="mb-2 text-xs font-bold text-muted">
                {String(stop.stop_type || stop.type || `Stop ${i + 1}`)} ·{" "}
                {String(stop.formatted || stop.address || "—")}
              </p>
              {stop.time_window_start || stop.time_window_end ? (
                <p className="mb-2 text-xs text-muted">
                  Window: {stop.time_window_start ? String(stop.time_window_start) : "?"} –{" "}
                  {stop.time_window_end ? String(stop.time_window_end) : "?"}
                </p>
              ) : null}
              {packages.map((pkg, j) => {
                const parcel = (pkg ?? {}) as Record<string, unknown>;
                return (
                  <div key={j} className="mb-3 last:mb-0 rounded-lg bg-gray-bg/40 p-2">
                    <p className="mb-2 text-xs font-semibold">Parcel {j + 1}</p>
                    {amendable ? (
                      <div className="grid gap-2 sm:grid-cols-2">
                        <label className="text-xs">
                          Weight kg
                          <input
                            className="mt-1 w-full rounded-lg border border-primary/15 px-2 py-1"
                            value={parcel.weight_kg == null ? "" : String(parcel.weight_kg)}
                            onChange={(event) =>
                              updateStopPackage(setStops, i, j, { weight_kg: event.target.value })
                            }
                          />
                        </label>
                        <label className="text-xs">
                          Notes
                          <input
                            className="mt-1 w-full rounded-lg border border-primary/15 px-2 py-1"
                            value={parcel.notes == null ? "" : String(parcel.notes)}
                            onChange={(event) =>
                              updateStopPackage(setStops, i, j, { notes: event.target.value })
                            }
                          />
                        </label>
                      </div>
                    ) : (
                      Object.entries(parcel).map(([k, v]) => (
                        <Row
                          key={k}
                          label={k.replace(/_/g, " ")}
                          value={v == null ? "—" : String(v)}
                        />
                      ))
                    )}
                  </div>
                );
              })}
              {!packages.length ? <p className="text-muted">No parcels on this stop.</p> : null}
            </div>
          );
        })}
        {amendable ? (
          <Button type="button" disabled={busy} onClick={() => void save()}>
            {busy ? "Saving…" : "Save parcels and re-quote"}
          </Button>
        ) : null}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {detail.packages.map((p, i) => (
        <div key={i} className="rounded-xl border border-primary/10 p-3 text-sm">
          <p className="mb-2 text-xs font-bold text-muted">Parcel {i + 1}</p>
          {Object.entries(p).map(([k, v]) => (
            <Row key={k} label={k.replace(/_/g, " ")} value={v == null ? "—" : String(v)} />
          ))}
        </div>
      ))}
      {!detail.packages.length && (
        <>
          <Row label="Type" value={detail.package_type || "—"} />
          <Row label="Weight" value={detail.weight_kg != null ? `${detail.weight_kg} kg` : "—"} />
          <Row label="Dimensions" value={detail.dimensions || "—"} />
          <Row
            label="Declared value"
            value={detail.declared_value_cents ? formatCents(detail.declared_value_cents) : "—"}
          />
        </>
      )}
    </div>
  );
}

export function updateStopPackage(
  setStops: (
    updater: (current: Array<Record<string, unknown>>) => Array<Record<string, unknown>>
  ) => void,
  stopIndex: number,
  parcelIndex: number,
  patch: Record<string, unknown>
) {
  setStops((current) =>
    current.map((stop, i) => {
      if (i !== stopIndex) return stop;
      const packages = Array.isArray(stop.packages) ? [...stop.packages] : [];
      const existing = (packages[parcelIndex] ?? {}) as Record<string, unknown>;
      const next = { ...existing, ...patch };
      if ("weight_kg" in patch) {
        const raw = String(patch.weight_kg ?? "");
        next.weight_kg = raw.trim() === "" ? null : Number(raw);
      }
      packages[parcelIndex] = next;
      return { ...stop, packages };
    })
  );
}

export function JourneySection({
  detail,
  tracking,
  live,
  onRefresh,
}: {
  detail: OrderDetail;
  tracking: Record<string, unknown> | null;
  live: Record<string, unknown> | null | undefined;
  onRefresh?: () => void;
}) {
  return (
    <div className="space-y-8">
      <SectionBlock title="Timeline">
        <TimelineTab detail={detail} />
      </SectionBlock>
      <SectionBlock title="Tracking">
        <TrackingTab detail={detail} tracking={tracking} live={live} />
      </SectionBlock>
      <SectionBlock title="Packages">
        <PackagesTab detail={detail} onRefresh={onRefresh} />
      </SectionBlock>
      <SectionBlock title="Pickup">
        <AddressTab title="Pickup" addr={detail.pickup_detail} />
      </SectionBlock>
      <SectionBlock title="Stops">
        <StopsTab stops={detail.additional_stops} />
      </SectionBlock>
      <SectionBlock title="Delivery">
        <AddressTab title="Delivery" addr={detail.dropoff_detail} />
      </SectionBlock>
    </div>
  );
}
