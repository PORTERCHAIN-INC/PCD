"use client";

import { GoogleMapsProvider, TrackEtaPanel, TrackRouteMap, formatEta } from "@porterchain/maps";
import { formatCents, type OrderLiveTracking, type OrderResult } from "@/lib/booking";
import { cn } from "@/lib/utils";

type LiveBag = NonNullable<OrderLiveTracking["live_tracking"]>;

type Props = {
  order: OrderResult;
  live: OrderLiveTracking | null;
  refreshing?: boolean;
  onRefresh?: () => void;
};

function km(meters?: number | null): string | null {
  if (typeof meters !== "number" || !Number.isFinite(meters)) return null;
  return `${(meters / 1000).toFixed(1)} km`;
}

function formatStamp(iso?: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function pickMapPolyline(liveData: LiveBag | null | undefined, inTransit: boolean) {
  const remaining = liveData?.eta?.polyline;
  const corridor = liveData?.optimized_route?.polyline;
  // Live remaining path when driver is moving; otherwise full corridor.
  if (inTransit && liveData?.driver_location && remaining) {
    return {
      polyline: remaining,
      source: "osrm" as const,
      label: "Live remaining route (OSRM)",
    };
  }
  if (corridor) {
    return {
      polyline: corridor,
      source: "valhalla" as const,
      label: "Planned corridor (Valhalla)",
    };
  }
  if (remaining) {
    return {
      polyline: remaining,
      source: "osrm" as const,
      label: "ETA path (OSRM)",
    };
  }
  return { polyline: null, source: null, label: null };
}

export default function CustomerLiveTrack({ order, live, refreshing, onRefresh }: Props) {
  const liveData = live?.live_tracking ?? null;
  const pickup = liveData?.pickup ?? order.pickup;
  const dropoff = liveData?.dropoff ?? order.dropoff;
  const driverLocation = liveData?.driver_location ?? null;
  const eta = liveData?.eta ?? null;
  const status = liveData?.delivery_status;
  const delivered = Boolean(status?.delivered);
  const inTransit = Boolean(status?.in_transit);
  const route = liveData?.optimized_route;
  const mapLine = pickMapPolyline(liveData, inTransit);

  const hasDriverPin = Boolean(driverLocation);
  const hasOsrm = Boolean(eta?.source === "osrm" || eta?.polyline);
  const hasValhalla = Boolean(route?.polyline);
  const lastUpdated = formatStamp(liveData?.last_updated) ?? (refreshing ? "Updating…" : null);

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          {order.logo_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={order.logo_url}
              alt={order.company_name ? `${order.company_name} logo` : "Shipper logo"}
              referrerPolicy="no-referrer"
              className="h-12 w-12 rounded-lg object-cover"
            />
          ) : null}
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">
              Shipment tracking
            </p>
            <h1 className="mt-1 font-mono text-xl font-bold text-secondary sm:text-2xl">
              {order.tracking_number}
            </h1>
            {order.goods_summary ? (
              <p className="mt-1 text-sm text-primary">
                {order.goods_summary}
                {order.vehicle_class ? ` · ${order.vehicle_class}` : ""}
              </p>
            ) : null}
            <p className="mt-2 flex flex-wrap items-center gap-2 text-sm">
              <span
                className={cn(
                  "rounded-full px-2.5 py-1 text-xs font-semibold",
                  delivered
                    ? "bg-emerald-50 text-emerald-800"
                    : inTransit
                      ? "bg-sky-50 text-sky-900"
                      : "bg-primary/5 text-primary"
                )}
              >
                {status?.label ?? order.state.replace(/_/g, " ")}
              </span>
              {lastUpdated ? (
                <span className="text-xs text-muted">Updated {lastUpdated}</span>
              ) : null}
              {refreshing ? <span className="text-xs text-secondary">Refreshing…</span> : null}
            </p>
            {order.company_name ? (
              <p className="mt-1 text-sm font-medium text-primary">{order.company_name}</p>
            ) : null}
            {order.tracking_page_message ? (
              <p className="mt-1 text-sm text-muted">{order.tracking_page_message}</p>
            ) : null}
          </div>
        </div>
        {onRefresh ? (
          <button
            type="button"
            onClick={onRefresh}
            className="rounded-xl border border-primary/15 bg-white px-3 py-2 text-xs font-semibold text-primary hover:bg-gray-bg"
          >
            Refresh
          </button>
        ) : null}
      </header>

      <div className="flex flex-wrap gap-2">
        <SourceChip
          active={hasDriverPin}
          label="Driver GPS"
          detail={hasDriverPin ? "Driver GPS (polled)" : "Waiting for driver GPS"}
        />
        <SourceChip
          active={hasOsrm}
          label="ETA"
          detail={
            eta?.source === "scheduled"
              ? "Scheduled window"
              : hasOsrm
                ? "Road remaining (OSRM)"
                : "ETA not available yet"
          }
        />
        <SourceChip
          active={hasValhalla}
          label="Route"
          detail={hasValhalla ? "Corridor (Valhalla)" : "No corridor yet"}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.4fr_0.9fr]">
        <section className="overflow-hidden rounded-2xl border border-primary/10 bg-white shadow-sm">
          <GoogleMapsProvider>
            <TrackRouteMap
              pickup={pickup as Record<string, unknown>}
              dropoff={dropoff as Record<string, unknown>}
              driverLocation={driverLocation}
              routePolyline={mapLine.polyline}
              height="min(62vw, 420px)"
              className="rounded-none border-0"
            />
          </GoogleMapsProvider>
          <div className="flex flex-wrap items-center gap-4 border-t border-primary/8 px-4 py-3 text-xs text-muted">
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" /> Pickup
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 rounded-full bg-rose-500" /> Drop-off
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 rounded-full bg-sky-500" /> Driver
            </span>
            {mapLine.label ? (
              <span className="flex items-center gap-1.5">
                <span className="inline-block h-0.5 w-4 bg-secondary" /> {mapLine.label}
              </span>
            ) : null}
          </div>
        </section>

        <aside className="space-y-4">
          <TrackEtaPanel eta={eta} delivered={delivered} />

          <section className="rounded-2xl border border-primary/10 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-primary">Route & engines</h2>
            <dl className="mt-3 space-y-2.5 text-sm">
              <Row
                label="Corridor"
                value={
                  route
                    ? [km(route.distance_meters), formatEta(route.duration_seconds)]
                        .filter(Boolean)
                        .join(" · ") || "Valhalla"
                    : "—"
                }
              />
              <Row
                label="Remaining"
                value={
                  eta?.source === "osrm"
                    ? [km(eta.distance_meters), eta.label ?? formatEta(eta.duration_seconds)]
                        .filter(Boolean)
                        .join(" · ")
                    : eta?.source === "scheduled"
                      ? `Scheduled ${eta.label ?? "—"}`
                      : "—"
                }
              />
              <Row
                label="Driver GPS"
                value={
                  driverLocation
                    ? `${driverLocation.lat.toFixed(4)}, ${driverLocation.lng.toFixed(4)}`
                    : "No pin yet"
                }
              />
              <Row
                label="Amount"
                value={formatCents(order.amount_cents, order.currency.toUpperCase())}
              />
            </dl>
          </section>
        </aside>
      </div>

      <section className="grid gap-3 rounded-2xl border border-primary/10 bg-white p-4 shadow-sm sm:grid-cols-2 sm:p-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">Pickup</p>
          <p className="mt-1.5 text-sm leading-relaxed text-primary">{pickup?.formatted ?? "—"}</p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">Drop-off</p>
          <p className="mt-1.5 text-sm leading-relaxed text-primary">{dropoff?.formatted ?? "—"}</p>
        </div>
        {order.scheduled_at ? (
          <div className="sm:col-span-2">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">
              Scheduled
            </p>
            <p className="mt-1.5 text-sm text-primary">
              {new Date(order.scheduled_at).toLocaleString()}
            </p>
          </div>
        ) : null}
      </section>

      <p className="text-xs leading-relaxed text-muted">
        Map shows pickup and drop-off pins, the planned corridor when available, and the driver pin
        once the van is moving. Road ETA uses the road engine when a live route exists. Refreshes
        every 10s (HTTP poll — not a map WebSocket).
      </p>
    </div>
  );
}

function SourceChip({ active, label, detail }: { active: boolean; label: string; detail: string }) {
  return (
    <div
      className={cn(
        "rounded-xl border px-3 py-2",
        active ? "border-secondary/25 bg-secondary/5" : "border-primary/8 bg-white"
      )}
    >
      <p className={cn("text-xs font-semibold", active ? "text-secondary" : "text-muted")}>
        {label}
        {active
          ? label === "Driver GPS"
            ? " · live"
            : label === "ETA"
              ? " · OSRM"
              : " · Valhalla"
          : ""}
      </p>
      <p className="mt-0.5 text-[0.7rem] text-muted">{detail}</p>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="text-muted">{label}</dt>
      <dd className="text-right font-medium text-primary">{value}</dd>
    </div>
  );
}
