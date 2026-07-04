"use client";

import { TrackingMap } from "@/components/tracking/TrackingMap";
import type { LiveTracking, TrackingDashboard } from "@/lib/tracking";
import Link from "next/link";

export function TrackingDashboardPanel({ dashboard }: { dashboard: TrackingDashboard }) {
  if (dashboard.active_count === 0) {
    return (
      <div className="rounded-2xl border border-primary/10 bg-white p-8 text-center">
        <p className="font-medium text-primary">No active deliveries</p>
        <p className="mt-1 text-sm text-muted">
          In-transit shipments will appear here with live driver positions.
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
          {dashboard.active_count} active · updated{" "}
          {new Date(dashboard.updated_at).toLocaleTimeString()}
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
              <p className="text-muted">{String(o.state).replace(/_/g, " ")}</p>
            </div>
            <div className="text-right">
              {(o.eta as { label?: string })?.label && (
                <p className="font-medium text-sky-700">{(o.eta as { label: string }).label}</p>
              )}
              <Link
                href={`/track?q=${encodeURIComponent(String(o.tracking_number))}`}
                className="text-secondary hover:underline"
              >
                Live track
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
