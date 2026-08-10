"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { EmptyState } from "@porterchain/ui/empty-state";
import { Spinner } from "@porterchain/ui/loading";
import CustomerShell from "@/components/CustomerShell";
import CustomerLiveTrack from "@/components/tracking/CustomerLiveTrack";
import {
  getOrderByTracking,
  getOrderLiveTracking,
  type OrderLiveTracking,
  type OrderResult,
} from "@/lib/booking";

const POLL_MS = 10_000;

export default function TrackOrderPage() {
  const params = useParams();
  const trackingNumber = typeof params.trackingNumber === "string" ? params.trackingNumber : "";
  const [order, setOrder] = useState<OrderResult | null>(null);
  const [live, setLive] = useState<OrderLiveTracking | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(
    async (mode: "initial" | "poll" | "manual" = "poll") => {
      if (!trackingNumber) return;
      if (mode === "initial") setLoading(true);
      if (mode === "manual" || mode === "poll") setRefreshing(true);
      setError("");
      try {
        const [orderResult, liveResult] = await Promise.all([
          getOrderByTracking(trackingNumber),
          getOrderLiveTracking(trackingNumber).catch(() => null),
        ]);
        setOrder(orderResult);
        setLive(liveResult);
      } catch {
        if (mode === "initial") {
          setError("Shipment not found.");
          setOrder(null);
          setLive(null);
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [trackingNumber]
  );

  useEffect(() => {
    void load("initial");
  }, [load]);

  useEffect(() => {
    if (!trackingNumber || !order) return;
    const delivered = Boolean(live?.live_tracking?.delivery_status?.delivered);
    if (delivered) return;
    const timer = window.setInterval(() => void load("poll"), POLL_MS);
    return () => window.clearInterval(timer);
  }, [trackingNumber, order, live?.live_tracking?.delivery_status?.delivered, load]);

  return (
    <CustomerShell>
      <div className="mb-5">
        <Link href="/dashboard" className="text-sm font-medium text-secondary hover:underline">
          ← Back to dashboard
        </Link>
      </div>

      {loading && <Spinner label="Loading live tracking…" />}
      {error && !loading && <EmptyState title="Shipment not found" hint={error} />}

      {order && !loading ? (
        <CustomerLiveTrack
          order={order}
          live={live}
          refreshing={refreshing}
          onRefresh={() => void load("manual")}
        />
      ) : null}
    </CustomerShell>
  );
}
