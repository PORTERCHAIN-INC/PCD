"use client";

import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { getOrder, trackOrder } from "@/lib/api";
import { formatCents, formatDate } from "@/lib/utils";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

export default function OrderDetailPage() {
  const { order_id } = useParams<{ order_id: string }>();
  const { getApiToken, orgId, isSignedIn, isLoaded } = useMerchantAuth();
  const [timeline, setTimeline] = useState<Array<Record<string, unknown>>>([]);
  const [order, setOrder] = useState<Awaited<ReturnType<typeof getOrder>> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded || !isSignedIn || !order_id) return;
    (async () => {
      try {
        const token = await getApiToken();
        const o = await getOrder(token, order_id, orgId);
        setOrder(o);
        const tracked = await trackOrder(token, o.tracking_number, orgId);
        setTimeline(tracked.timeline);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load order");
      }
    })();
  }, [getApiToken, orgId, isLoaded, isSignedIn, order_id]);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!order) return <p className="text-muted">Loading…</p>;

  return (
    <div className="space-y-6">
      <Link href="/orders" className="text-sm text-secondary hover:underline">
        ← Back to orders
      </Link>
      <div>
        <h1 className="text-2xl font-bold text-primary">{order.tracking_number}</h1>
        <p className="text-sm text-muted">
          {order.state} · {formatCents(order.amount_cents)} · {formatDate(order.scheduled_at)}
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <InfoCard title="Pickup" value={order.pickup?.formatted || "—"} />
        <InfoCard title="Dropoff" value={order.dropoff?.formatted || "—"} />
        <InfoCard title="PO Number" value={order.purchase_order_number || "—"} />
        <InfoCard title="Internal ref" value={order.internal_reference || "—"} />
      </div>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Tracking timeline</h2>
        <ol className="mt-4 space-y-3">
          {timeline.length === 0 && <li className="text-sm text-muted">No events yet</li>}
          {timeline.map((ev, i) => (
            <li key={i} className="border-l-2 border-secondary/30 pl-4 text-sm">
              <span className="font-medium">{String(ev.event_type)}</span>
              {ev.to_state ? <span className="text-muted"> → {String(ev.to_state)}</span> : null}
              <div className="text-xs text-muted">{String(ev.occurred_at || "")}</div>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}

function InfoCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-xl border border-primary/10 bg-white p-4">
      <p className="text-xs text-muted">{title}</p>
      <p className="mt-1 text-sm font-medium">{value}</p>
    </div>
  );
}
