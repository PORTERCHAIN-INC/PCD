"use client";

import { use, useCallback, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import OrderDetailView, { type Order360Actions } from "@/components/orders/OrderDetailView";
import { AssignDriverModal } from "@/components/orders/AssignDriverModal";
import { downloadOrderPdf, ordersApi } from "@/lib/orders";

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

  const [assignOpen, setAssignOpen] = useState(false);

  const actions: Order360Actions = useMemo(
    () => ({
      onAssignDriver: () => setAssignOpen(true),
      onReassignDriver: () => setAssignOpen(true),
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
        void (async () => {
          try {
            const token = await getApiToken();
            const res = await ordersApi.generateInvoice(token, id);
            window.alert(`Invoice ${res.invoice_number} ready.`);
            await invalidate();
          } catch (err) {
            window.alert(err instanceof Error ? err.message : "Invoice generation failed");
          }
        })();
      },
      onResendReceipt: () => {
        void (async () => {
          try {
            const token = await getApiToken();
            const res = await ordersApi.resendReceipt(token, id);
            window.alert(
              res.email
                ? `Receipt resent to ${res.email}`
                : "Receipt event queued (no recipient email on file)."
            );
            await invalidate();
          } catch (err) {
            window.alert(err instanceof Error ? err.message : "Resend receipt failed");
          }
        })();
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
      onPrintLabels: () => {
        void (async () => {
          try {
            const token = await getApiToken();
            await downloadOrderPdf(
              token,
              ordersApi.labelPdfUrl(id),
              `label-${detail?.tracking_number ?? id}.pdf`
            );
          } catch (err) {
            window.alert(err instanceof Error ? err.message : "Label PDF failed");
          }
        })();
      },
      onPrintManifest: () => {
        void (async () => {
          try {
            const token = await getApiToken();
            await downloadOrderPdf(
              token,
              ordersApi.manifestPdfUrl(id),
              `manifest-${detail?.tracking_number ?? id}.pdf`
            );
          } catch (err) {
            window.alert(err instanceof Error ? err.message : "Manifest PDF failed");
          }
        })();
      },
    }),
    [detail, getApiToken, id, invalidate, router]
  );

  return (
    <>
      <OrderDetailView
        detail={detail ?? null}
        tracking={tracking ?? null}
        loading={isLoading}
        error={isError ? (error instanceof Error ? error.message : "Failed to load order") : null}
        liveRefreshing={isFetching && !isLoading}
        actions={actions}
        onRefresh={() => void invalidate()}
      />
      <AssignDriverModal
        open={assignOpen}
        orderId={id}
        trackingNumber={detail?.tracking_number}
        currentDriverName={detail?.driver_name}
        onClose={() => setAssignOpen(false)}
        onAssigned={() => void invalidate()}
      />
    </>
  );
}
