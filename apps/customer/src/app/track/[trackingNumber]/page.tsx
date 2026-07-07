"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import CustomerShell from "@/components/CustomerShell";
import { formatCents, getOrderByTracking, type OrderResult } from "@/lib/booking";

export default function TrackOrderPage() {
  const params = useParams();
  const trackingNumber = typeof params.trackingNumber === "string" ? params.trackingNumber : "";
  const [order, setOrder] = useState<OrderResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!trackingNumber) return;
    (async () => {
      setLoading(true);
      setError("");
      try {
        setOrder(await getOrderByTracking(trackingNumber));
      } catch {
        setError("Shipment not found.");
        setOrder(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [trackingNumber]);

  return (
    <CustomerShell>
      <div className="mb-6">
        <Link href="/dashboard" className="text-sm font-medium text-secondary hover:underline">
          ← Back to dashboard
        </Link>
      </div>

      {loading && <p className="text-sm text-muted">Loading shipment…</p>}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {order && (
        <section className="rounded-2xl border border-primary/10 bg-white p-6 shadow-sm">
          <h1 className="text-xl font-bold text-primary">Shipment tracking</h1>
          <p className="mt-2 font-mono text-secondary">{order.tracking_number}</p>
          <p className="mt-4 text-sm">
            Status: <span className="font-semibold text-primary">{order.state}</span>
          </p>
          <p className="mt-2 text-sm text-muted">
            {formatCents(order.amount_cents, order.currency.toUpperCase())}
          </p>
          <ul className="mt-6 space-y-3 text-sm">
            <li>
              <span className="text-muted">Pickup: </span>
              {order.pickup?.formatted ?? "—"}
            </li>
            <li>
              <span className="text-muted">Drop-off: </span>
              {order.dropoff?.formatted ?? "—"}
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
