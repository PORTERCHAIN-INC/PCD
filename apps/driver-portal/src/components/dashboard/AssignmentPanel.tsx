import Link from "next/link";
import { ArrowRight, MapPin, Package, Truck } from "lucide-react";
import type { DriverRoute, DriverStop } from "@/lib/api";
import type { DriverNextStop } from "@/lib/jobs";
import { formatStopAddress } from "@/lib/workspace";
import { cn } from "@/lib/utils";

function StopRow({ stop, highlight }: { stop: DriverStop; highlight?: boolean }) {
  return (
    <li
      className={cn(
        "flex items-start gap-3 rounded-xl px-3 py-2.5",
        highlight ? "bg-[var(--secondary)]/8 border border-[var(--secondary)]/20" : "bg-[var(--gray-bg)]"
      )}
    >
      <span
        className={cn(
          "mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs font-bold uppercase",
          stop.stop_type === "pickup"
            ? "bg-blue-100 text-blue-700"
            : "bg-emerald-100 text-emerald-700"
        )}
      >
        {stop.stop_type === "pickup" ? "P" : "D"}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{formatStopAddress(stop)}</p>
        <p className="text-xs text-[var(--muted)]">
          {stop.order_number} · {stop.status.replace(/_/g, " ")}
        </p>
      </div>
    </li>
  );
}

export function AssignmentPanel({
  route,
  nextStop,
  apiNextStop,
  pickupQueue,
  deliveryQueue,
}: {
  route: DriverRoute | null;
  nextStop: DriverStop | null;
  apiNextStop?: DriverNextStop | null;
  pickupQueue: DriverStop[];
  deliveryQueue: DriverStop[];
}) {
  const resolved = apiNextStop
    ? {
        label: apiNextStop.formatted_address,
        orderNumber: apiNextStop.order_number ?? "",
        stopType: apiNextStop.stop_type,
        orderId: apiNextStop.order_id,
        distance: apiNextStop.distance_m,
        eta: apiNextStop.eta_minutes,
      }
    : nextStop
      ? {
          label: formatStopAddress(nextStop),
          orderNumber: nextStop.order_number,
          stopType: nextStop.stop_type,
          orderId: nextStop.order_id,
          distance: null as number | null | undefined,
          eta: null as number | null | undefined,
        }
      : null;
  return (
    <div className="rounded-2xl border border-transparent bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold">Current Assignment</h2>
          <p className="text-sm text-[var(--muted)]">
            {route
              ? `Route ${route.route_id.replace("route-", "")} · ${route.status.replace(/_/g, " ")}`
              : "No active route assigned"}
          </p>
        </div>
        {route && (
          <Link
            href="/jobs"
            className="inline-flex items-center gap-1 text-sm font-semibold text-[var(--secondary)] hover:underline"
          >
            View all
            <ArrowRight className="h-4 w-4" />
          </Link>
        )}
      </div>

      {resolved ? (
        <div className="mt-4 rounded-xl border border-[var(--secondary)]/25 bg-gradient-to-br from-[var(--secondary)]/5 to-transparent p-4">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--secondary)]">
            <MapPin className="h-4 w-4" />
            Next Stop
          </div>
          <p className="mt-2 text-base font-bold">{resolved.label}</p>
          <p className="mt-1 text-sm text-[var(--muted)]">
            {resolved.stopType === "pickup" ? "Pickup" : "Delivery"} · {resolved.orderNumber}
            {resolved.eta != null ? ` · ~${resolved.eta} min` : ""}
            {resolved.distance != null ? ` · ${(resolved.distance / 1000).toFixed(1)} km` : ""}
          </p>
          <Link
            href={`/jobs/${resolved.orderId}`}
            className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-[var(--secondary)] hover:underline"
          >
            Open job
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      ) : (
        <p className="mt-4 rounded-xl bg-[var(--gray-bg)] px-4 py-6 text-center text-sm text-[var(--muted)]">
          {route ? "All stops completed for this route" : "Check back when a route is assigned"}
        </p>
      )}

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-[var(--primary)]">
            <Package className="h-4 w-4 text-blue-600" />
            Pickup Queue
            <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
              {pickupQueue.length}
            </span>
          </div>
          {pickupQueue.length === 0 ? (
            <p className="text-xs text-[var(--muted)]">No pending pickups</p>
          ) : (
            <ul className="space-y-2">
              {pickupQueue.slice(0, 3).map((s) => (
                <StopRow key={s.stop_id} stop={s} />
              ))}
            </ul>
          )}
        </div>
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-[var(--primary)]">
            <Truck className="h-4 w-4 text-emerald-600" />
            Delivery Queue
            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700">
              {deliveryQueue.length}
            </span>
          </div>
          {deliveryQueue.length === 0 ? (
            <p className="text-xs text-[var(--muted)]">No pending deliveries</p>
          ) : (
            <ul className="space-y-2">
              {deliveryQueue.slice(0, 3).map((s) => (
                <StopRow key={s.stop_id} stop={s} />
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
