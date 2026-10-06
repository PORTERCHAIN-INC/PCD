"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { EmptyState } from "@porterchain/ui/empty-state";
import { PageSkeleton } from "@porterchain/ui/loading";
import CustomerLiveTrack from "@/components/tracking/CustomerLiveTrack";
import {
  getOrderByTracking,
  getOrderLiveTracking,
  type OrderLiveTracking,
  type OrderResult,
} from "@/lib/booking";

const POLL_MS = 10_000;

export default function TrackOrderClient({ trackingNumber }: { trackingNumber: string }) {
  const orderQuery = useQuery({
    queryKey: ["customer-track-order", trackingNumber],
    enabled: Boolean(trackingNumber),
    queryFn: () => getOrderByTracking(trackingNumber),
  });

  const liveQuery = useQuery({
    queryKey: ["customer-track-live", trackingNumber],
    enabled: Boolean(trackingNumber),
    queryFn: () => getOrderLiveTracking(trackingNumber).catch(() => null),
    refetchInterval: (q) => {
      const live = q.state.data as OrderLiveTracking | null | undefined;
      if (live?.live_tracking?.delivery_status?.delivered) return false;
      if (!orderQuery.data) return false;
      return POLL_MS;
    },
  });

  const order = (orderQuery.data ?? null) as OrderResult | null;
  const live = (liveQuery.data ?? null) as OrderLiveTracking | null;
  const loading = orderQuery.isLoading && !order;
  const error = orderQuery.isError && !order ? "Shipment not found." : "";
  const refreshing = orderQuery.isFetching || liveQuery.isFetching;

  return (
    <>
      <div className="mb-5">
        <Link href="/dashboard" className="text-sm font-medium text-secondary hover:underline">
          ← Back to dashboard
        </Link>
      </div>

      {loading ? <PageSkeleton rows={5} /> : null}
      {error && !loading ? <EmptyState title="Shipment not found" hint={error} /> : null}

      {order ? (
        <CustomerLiveTrack
          order={order}
          live={live}
          refreshing={refreshing}
          onRefresh={() => {
            void orderQuery.refetch();
            void liveQuery.refetch();
          }}
        />
      ) : null}
    </>
  );
}
