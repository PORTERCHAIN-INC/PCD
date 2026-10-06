"use client";

import dynamic from "next/dynamic";
import WithGoogleMaps from "@/components/maps/WithGoogleMaps";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { useMerchantRealtime } from "@/hooks/useMerchantRealtime";
import { ordersApi, type OrderDetail } from "@/lib/orders";
import type { LiveTracking } from "@/lib/tracking";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Suspense, useCallback } from "react";

const Order360View = dynamic(
  () => import("@/components/orders/Order360View").then((m) => m.Order360View),
  { loading: () => <PageSkeleton rows={5} /> }
);

export default function OrderDetailClient({ orderId }: { orderId: string }) {
  return (
    <Suspense fallback={<PageSkeleton rows={5} />}>
      <WithGoogleMaps>
        <OrderDetailInner orderId={orderId} />
      </WithGoogleMaps>
    </Suspense>
  );
}

function OrderDetailInner({ orderId }: { orderId: string }) {
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const qc = useQueryClient();
  const keyOrg = orgId ?? null;
  const ready = Boolean(isLoaded && isSignedIn && orgId && orderId);

  const detailQuery = useQuery({
    queryKey: ["merchant-order-360", keyOrg, orderId],
    enabled: ready,
    queryFn: async () => {
      const token = await getApiToken();
      return ordersApi.detail360(token, orderId, orgId);
    },
  });

  const trackingQuery = useQuery({
    queryKey: ["merchant-order-tracking", keyOrg, orderId],
    enabled: ready,
    queryFn: async () => {
      const token = await getApiToken();
      return ordersApi.tracking(token, orderId, orgId).catch(() => null);
    },
  });

  const refresh = useCallback(async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["merchant-order-360", keyOrg, orderId] }),
      qc.invalidateQueries({ queryKey: ["merchant-order-tracking", keyOrg, orderId] }),
    ]);
  }, [qc, keyOrg, orderId]);

  useMerchantRealtime(ready, orgId, getApiToken, refresh);

  const detail = detailQuery.data as OrderDetail | undefined;
  const tracking = (trackingQuery.data ?? null) as LiveTracking | null;
  const error = detailQuery.error instanceof Error ? detailQuery.error.message : null;

  if (isLoaded && !isSignedIn) return <p className="text-muted">Please sign in.</p>;
  if (error && !detail) return <p className="text-red-600">{error}</p>;
  if (!detail) return <PageSkeleton rows={5} />;

  return (
    <Order360View
      detail={detail}
      tracking={tracking}
      liveRefreshing={detailQuery.isFetching || trackingQuery.isFetching}
      onRefresh={() => void refresh()}
      onDuplicate={() => {
        void (async () => {
          const token = await getApiToken();
          await ordersApi.bulk(token, [orderId], "duplicate", orgId);
          await refresh();
        })();
      }}
      getApiToken={getApiToken}
      orgId={orgId}
    />
  );
}
