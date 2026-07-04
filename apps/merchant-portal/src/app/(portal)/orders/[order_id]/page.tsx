"use client";

import { Order360View } from "@/components/orders/Order360View";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { useMerchantRealtime } from "@/hooks/useMerchantRealtime";
import type { LiveTracking } from "@/lib/tracking";
import { ordersApi, printOrderLabels, type OrderDetail } from "@/lib/orders";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

const TRACKING_POLL_MS = 10_000;

export default function OrderDetailPage() {
  const { order_id } = useParams<{ order_id: string }>();
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const [detail, setDetail] = useState<OrderDetail | null>(null);
  const [tracking, setTracking] = useState<LiveTracking | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const refresh = useCallback(async () => {
    if (!isSignedIn || !order_id) return;
    setRefreshing(true);
    try {
      const token = await getApiToken();
      const [d, t] = await Promise.all([
        ordersApi.detail360(token, order_id, orgId),
        ordersApi.tracking(token, order_id, orgId),
      ]);
      setDetail(d);
      setTracking(t);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load order");
    } finally {
      setRefreshing(false);
    }
  }, [getApiToken, isSignedIn, order_id, orgId]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn || !order_id) return;
    void refresh();
  }, [isLoaded, isSignedIn, order_id, refresh]);

  useEffect(() => {
    if (!isSignedIn || !order_id) return;
    const timer = setInterval(() => void refresh(), TRACKING_POLL_MS);
    return () => clearInterval(timer);
  }, [isSignedIn, order_id, refresh]);

  useMerchantRealtime(isLoaded && isSignedIn, orgId, getApiToken, refresh);

  if (error && !detail) return <p className="text-red-600">{error}</p>;
  if (!detail) return <p className="text-muted">Loading order…</p>;

  return (
    <Order360View
      detail={detail}
      tracking={tracking}
      liveRefreshing={refreshing}
      onRefresh={() => void refresh()}
      onCancel={() => {
        void (async () => {
          if (!window.confirm("Cancel this order?")) return;
          const token = await getApiToken();
          await ordersApi.bulk(token, [order_id], "cancel", orgId);
          await refresh();
        })();
      }}
      onDuplicate={() => {
        void (async () => {
          const token = await getApiToken();
          await ordersApi.bulk(token, [order_id], "duplicate", orgId);
          await refresh();
        })();
      }}
      onPrintLabels={() => printOrderLabels([detail])}
      getApiToken={getApiToken}
      orgId={orgId}
    />
  );
}
