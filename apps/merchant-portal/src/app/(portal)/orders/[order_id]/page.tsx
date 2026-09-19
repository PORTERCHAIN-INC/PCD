"use client";

import { Order360View } from "@/components/orders/Order360View";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { useMerchantRealtime } from "@/hooks/useMerchantRealtime";
import type { LiveTracking } from "@/lib/tracking";
import { ordersApi, type OrderDetail } from "@/lib/orders";
import { useParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

const TRACKING_POLL_MS = 10_000;

export default function OrderDetailPage() {
  return (
    <Suspense fallback={<p className="text-muted">Loading order…</p>}>
      <OrderDetailPageInner />
    </Suspense>
  );
}

function OrderDetailPageInner() {
  const { order_id } = useParams<{ order_id: string }>();
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const [detail, setDetail] = useState<OrderDetail | null>(null);
  const [tracking, setTracking] = useState<LiveTracking | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const ready = Boolean(isLoaded && isSignedIn && orgId && order_id);

  const refresh = useCallback(async () => {
    if (!isSignedIn || !orgId || !order_id) return;
    setRefreshing(true);
    try {
      const token = await getApiToken();
      const [d, t] = await Promise.all([
        ordersApi.detail360(token, order_id, orgId),
        ordersApi.tracking(token, order_id, orgId).catch(() => null),
      ]);
      setDetail(d);
      setTracking(t);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "That order was not found.");
    } finally {
      setRefreshing(false);
    }
  }, [getApiToken, isSignedIn, order_id, orgId]);

  useEffect(() => {
    if (!ready) return;
    void refresh();
  }, [ready, refresh]);

  useEffect(() => {
    if (!ready) return;
    const timer = setInterval(() => void refresh(), TRACKING_POLL_MS);
    return () => clearInterval(timer);
  }, [ready, refresh]);

  useMerchantRealtime(ready, orgId, getApiToken, refresh);

  if (!isLoaded) return <p className="text-muted">Loading…</p>;
  if (!isSignedIn) return <p className="text-muted">Please sign in.</p>;
  if (!orgId) return <p className="text-muted">Loading company…</p>;
  if (error && !detail) return <p className="text-red-600">{error}</p>;
  if (!detail) return <p className="text-muted">Loading order…</p>;

  return (
    <Order360View
      detail={detail}
      tracking={tracking}
      liveRefreshing={refreshing}
      onRefresh={() => void refresh()}
      onDuplicate={() => {
        void (async () => {
          const token = await getApiToken();
          await ordersApi.bulk(token, [order_id], "duplicate", orgId);
          await refresh();
        })();
      }}
      getApiToken={getApiToken}
      orgId={orgId}
    />
  );
}
