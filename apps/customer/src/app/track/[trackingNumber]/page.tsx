"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { GoogleMapsProvider, TrackEtaPanel, TrackRouteMap } from "@porterchain/maps";
import { EmptyState } from "@porterchain/ui/empty-state";
import { Spinner } from "@porterchain/ui/loading";
import CustomerShell from "@/components/CustomerShell";
import {
  formatCents,
  getOrderByTracking,
  getOrderLiveTracking,
  type OrderLiveTracking,
  type OrderResult,
} from "@/lib/booking";

export default function TrackOrderPage() {
  const params = useParams();
  const trackingNumber = typeof params.trackingNumber === "string" ? params.trackingNumber : "";
  const [order, setOrder] = useState<OrderResult | null>(null);
  const [live, setLive] = useState<OrderLiveTracking | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!trackingNumber) return;
    (async () => {
      setLoading(true);
      setError("");
      try {
        const [orderResult, liveResult] = await Promise.all([
          getOrderByTracking(trackingNumber),
          getOrderLiveTracking(trackingNumber).catch(() => null),
        ]);
        setOrder(orderResult);
        setLive(liveResult);
      } catch {
        setError("Shipment not found.");
        setOrder(null);
        setLive(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [trackingNumber]);

  const liveData = live?.live_tracking;
  const pickup = liveData?.pickup ?? order?.pickup;
  const dropoff = liveData?.dropoff ?? order?.dropoff;
  const driverLocation = liveData?.driver_location ?? null;
  const routePolyline = liveData?.optimized_route?.polyline ?? liveData?.eta?.polyline ?? null;
  const eta = liveData?.eta ?? null;
  const delivered = Boolean(liveData?.delivery_status?.delivered);

  return (
    <CustomerShell>
      <div className="mb-6">
        <Link href="/dashboard" className="text-sm font-medium text-secondary hover:underline">
          ← Back to dashboard
        </Link>
      </div>

      {loading && <Spinner label="Loading shipment…" />}
      {error && !loading && <EmptyState title="Shipment not found" hint={error} />}

      {order && (
        <section className="rounded-2xl border border-primary/10 bg-white p-6 shadow-sm">
          <h1 className="text-xl font-bold text-primary">Shipment tracking</h1>
          <p className="mt-2 font-mono text-secondary">{order.tracking_number}</p>
          <GoogleMapsProvider>
            <TrackRouteMap
              pickup={pickup}
              dropoff={dropoff}
              driverLocation={driverLocation}
              routePolyline={routePolyline}
              height="min(55vw, 320px)"
              className="mt-6"
            />
          </GoogleMapsProvider>
          <TrackEtaPanel eta={eta} delivered={delivered} className="mt-4" />
          <p className="mt-4 text-sm">
            Status: <span className="font-semibold text-primary">{order.state}</span>
          </p>
          <p className="mt-2 text-sm text-muted">
            {formatCents(order.amount_cents, order.currency.toUpperCase())}
          </p>
          <ul className="mt-6 space-y-3 text-sm">
            <li>
              <span className="text-muted">Pickup: </span>
              {pickup?.formatted ?? "—"}
            </li>
            <li>
              <span className="text-muted">Drop-off: </span>
              {dropoff?.formatted ?? "—"}
            </li>
            {order.scheduled_at && (
              <li>
                <span className="text-muted">Scheduled: </span>
                {new Date(order.scheduled_at).toLocaleString()}
              </li>
            )}
          </ul>
        </section>
      )}
    </CustomerShell>
  );
}
