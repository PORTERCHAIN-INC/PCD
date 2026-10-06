"use client";

import { TrackingMap } from "@/components/tracking/TrackingMap";
import { orderStateLabel } from "@/lib/catalog";
import type { LiveTracking, TrackingDashboard } from "@/lib/tracking";
import { formatDate } from "@/lib/utils";
import { etaSourceLabel } from "@porterchain/maps";
import Link from "next/link";

export function TrackingDashboardPanel({ dashboard }: { dashboard: TrackingDashboard }) {
  if (dashboard.active_count === 0) {
    return (
      <div className="rounded-2xl border border-primary/10 bg-white p-8 text-center">
        <p className="font-medium text-primary">No active deliveries</p>
        <p className="mt-1 text-sm text-muted">
          In-transit shipments will appear here with the driver pin while the job is moving.
        </p>
      </div>
    );
  }

  const first = dashboard.orders[0] as Record<string, unknown>;
  const mapTracking: LiveTracking = {
    order_id: String(first.order_id ?? ""),
    tracking_number: String(first.tracking_number ?? ""),
    state: String(first.state ?? ""),
    pickup: first.pickup as Record<string, unknown>,
    dropoff: first.dropoff as Record<string, unknown>,
    driver_location: first.driver_location as { lat: number; lng: number } | undefined,
    geofences: dashboard.geofences,
    eta: first.eta as LiveTracking["eta"],
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted">
          {dashboard.active_count} active · updated {formatDate(dashboard.updated_at)}
        </p>
      </div>
      <TrackingMap tracking={mapTracking} height="360px" />
      <ul className="divide-y divide-primary/10 rounded-2xl border border-primary/10 bg-white">
        {dashboard.orders.map((o) => (
          <li
            key={String(o.order_id)}
            className="flex items-center justify-between gap-4 px-4 py-3 text-sm"
          >
            <div>
              <p className="font-mono font-medium">{String(o.tracking_number)}</p>
              <p className="text-muted">
                {o.order_number ? `${String(o.order_number)} · ` : ""}
                {orderStateLabel(String(o.display_state || o.state))}
              </p>
            </div>
            <div className="flex flex-col items-end gap-1 text-right">
              {(o.eta as { label?: string; source?: string } | undefined)?.label && (
                <>
                  <p className="font-medium text-sky-700">{(o.eta as { label: string }).label}</p>
                  <p className="text-[11px] text-muted">
                    {etaSourceLabel((o.eta as { source?: string }).source) ?? "ETA"}
                  </p>
                </>
              )}
              <div className="flex gap-3">
                {o.order_id ? (
                  <Link
                    href={`/orders/${String(o.order_id)}?tab=tracking`}
                    className="text-secondary hover:underline"
                  >
                    Order
                  </Link>
                ) : null}
                <Link
                  href={`/track?q=${encodeURIComponent(String(o.tracking_number))}`}
                  className="text-secondary hover:underline"
                >
                  Track
                </Link>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
