"use client";

import { use, useCallback, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import OrderDetailView, { type Order360Actions } from "@/components/orders/OrderDetailView";
import { api } from "@/lib/api";
import { ordersApi } from "@/lib/orders";

const DETAIL_POLL_MS = 10_000;
const TRACKING_POLL_MS = 8_000;

export default function OrderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();

  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");

  const {
    data: detail,
    isLoading,
    isFetching,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["order", id],
    enabled,
    refetchInterval: DETAIL_POLL_MS,
    queryFn: async () => {
      const token = await getApiToken();
      return ordersApi.detail(token, id);
    },
  });

  const { data: tracking } = useQuery({
    queryKey: ["order-tracking", id],
    enabled: enabled && Boolean(detail),
    refetchInterval: TRACKING_POLL_MS,
    queryFn: async () => {
      const token = await getApiToken();
      return ordersApi.tracking(token, id);
    },
  });

  const invalidate = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ["order", id] });
    await queryClient.invalidateQueries({ queryKey: ["order-tracking", id] });
    await refetch();
  }, [queryClient, id, refetch]);

  const assignDriver = useCallback(async () => {
    const driverId = window.prompt("Enter driver ID to assign:");
    if (!driverId?.trim()) return;
    const token = await getApiToken();
    await api.assignDriver(token, id, driverId.trim());
    await invalidate();
  }, [getApiToken, id, invalidate]);

  const actions: Order360Actions = useMemo(
    () => ({
      onAssignDriver: () => void assignDriver(),
      onReassignDriver: () => void assignDriver(),
      onCancel: () => {
        void (async () => {
          if (!window.confirm("Cancel this order?")) return;
          const token = await getApiToken();
          await ordersApi.bulk(token, [id], "cancel");
          await invalidate();
        })();
      },
      onDuplicate: () => {
        window.alert(
          "Duplicate order uses the existing booking flow — open the linked booking draft to re-create."
        );
        if (detail?.booking_draft_id) router.push(`/booking-drafts/${detail.booking_draft_id}`);
      },
      onRebook: () => {
        if (detail?.booking_id) router.push(`/bookings/${detail.booking_id}`);
        else if (detail?.booking_draft_id)
          router.push(`/booking-drafts/${detail.booking_draft_id}`);
        else window.alert("No booking linked to this order.");
      },
      onCreateReturn: () => router.push(`/claims?order_id=${id}`),
      onGenerateInvoice: () => {
        if (detail?.invoice_number) router.push(`/finance/invoices`);
        else
          window.alert(
            "Invoice generation is handled by the billing engine when the order reaches POD_COMPLETED."
          );
      },
      onRefund: () => {
        window.alert("Refunds are processed through Finance — open the linked payment or invoice.");
        router.push("/finance");
      },
      onOpenClaim: () => router.push(`/claims?order_id=${id}`),
      onOpenSupport: () => router.push(`/support?order_id=${id}`),
      onShareTracking: () => {
        const url = `${window.location.origin}/track/${detail?.tracking_number ?? id}`;
        void navigator.clipboard.writeText(url).then(() => window.alert("Tracking link copied."));
      },
      onPrintLabels: () => window.print(),
      onPrintManifest: () => window.print(),
    }),
    [assignDriver, detail, getApiToken, id, invalidate, router]
  );

  return (
    <OrderDetailView
      detail={detail ?? null}
      tracking={tracking ?? null}
      loading={isLoading}
      error={isError ? (error instanceof Error ? error.message : "Failed to load order") : null}
      liveRefreshing={isFetching && !isLoading}
      actions={actions}
    />
  );
}
