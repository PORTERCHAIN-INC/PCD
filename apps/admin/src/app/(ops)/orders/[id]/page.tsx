"use client";

import { use, useCallback, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import OrderDetailView, { type Order360Actions } from "@/components/orders/OrderDetailView";
import { AssignDriverModal } from "@/components/orders/AssignDriverModal";
import {
  ExceptionReasonModal,
  type ExceptionColumn,
} from "@/components/orders/ExceptionReasonModal";
import { OrderBuilderModal, type OrderBuilderPrefill } from "@/components/orders/OrderBuilderModal";
import { downloadOrderFile, ordersApi, type OrderDetail } from "@/lib/orders";
import { ops } from "@/lib/operations";

const DETAIL_POLL_MS = 10_000;
const TRACKING_POLL_MS = 8_000;

function strField(rec: Record<string, unknown> | null | undefined, keys: string[]): string {
  if (!rec) return "";
  for (const k of keys) {
    const v = rec[k];
    if (typeof v === "string" && v.trim()) return v.trim();
  }
  return "";
}

function numField(rec: Record<string, unknown> | null | undefined, keys: string[]): string {
  if (!rec) return "";
  for (const k of keys) {
    const v = rec[k];
    if (typeof v === "number" && Number.isFinite(v)) return String(v);
    if (typeof v === "string" && v.trim() && !Number.isNaN(Number(v))) return v.trim();
  }
  return "";
}

function prefillFromDetail(detail: OrderDetail, title: string): OrderBuilderPrefill {
  const pickupAddr =
    strField(detail.pickup_detail, ["formatted_address", "formatted", "address", "street1"]) ||
    detail.pickup;
  const dropAddr =
    strField(detail.dropoff_detail, ["formatted_address", "formatted", "address", "street1"]) ||
    detail.destination;
  const stops: NonNullable<OrderBuilderPrefill["stops"]> = [
    {
      type: "pickup",
      formatted: pickupAddr,
      lat: numField(detail.pickup_detail, ["lat", "latitude"]),
      lng: numField(detail.pickup_detail, ["lng", "longitude", "lon"]),
    },
    {
      type: "dropoff",
      formatted: dropAddr,
      lat: numField(detail.dropoff_detail, ["lat", "latitude"]),
      lng: numField(detail.dropoff_detail, ["lng", "longitude", "lon"]),
    },
  ];
  for (const raw of detail.additional_stops) {
    if (!raw || typeof raw !== "object") continue;
    const stop = raw as Record<string, unknown>;
    const typeRaw = String(stop.type ?? stop.stop_type ?? "dropoff").toLowerCase();
    stops.push({
      type: typeRaw.includes("pick") ? "pickup" : "dropoff",
      formatted: strField(stop, ["formatted_address", "formatted", "address", "street1"]) || "—",
      lat: numField(stop, ["lat", "latitude"]),
      lng: numField(stop, ["lng", "longitude", "lon"]),
      notes: strField(stop, ["notes", "instructions"]) || undefined,
    });
  }
  return {
    title,
    merchant_id: detail.merchant_id,
    vehicle_class: detail.vehicle_class,
    special_instructions: detail.special_instructions,
    stops,
  };
}

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
  const [exceptionOpen, setExceptionOpen] = useState(false);
  const [exceptionInitial, setExceptionInitial] = useState<ExceptionColumn | "">("");
  const [builderOpen, setBuilderOpen] = useState(false);
  const [builderPrefill, setBuilderPrefill] = useState<OrderBuilderPrefill | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const flashError = useCallback((message: string) => {
    setActionNotice(null);
    setActionError(message);
  }, []);

  const flashNotice = useCallback((message: string) => {
    setActionError(null);
    setActionNotice(message);
  }, []);

  const openBuilderFromDetail = useCallback(
    (title: string) => {
      if (!detail) return;
      setBuilderPrefill(prefillFromDetail(detail, title));
      setBuilderOpen(true);
    },
    [detail]
  );

  const actions: Order360Actions = useMemo(
    () => ({
      onAssignDriver: () => setAssignOpen(true),
      onReassignDriver: () => setAssignOpen(true),
      onMarkException: (suggested?: string) => {
        const col =
          suggested === "failed" ||
          suggested === "returned" ||
          suggested === "lost" ||
          suggested === "damaged"
            ? suggested
            : "";
        setExceptionInitial(col);
        setExceptionOpen(true);
      },
      onCancel: () => {
        void (async () => {
          if (!window.confirm("Cancel this order?")) return;
          try {
            const token = await getApiToken();
            await ordersApi.bulk(token, [id], "cancel");
            flashNotice("Order cancelled.");
            await invalidate();
          } catch (err) {
            flashError(err instanceof Error ? err.message : "Cancel failed");
          }
        })();
      },
      onDuplicate: () => {
        if (detail?.booking_draft_id) {
          router.push(`/booking-drafts/${detail.booking_draft_id}`);
          return;
        }
        openBuilderFromDetail("Duplicate order");
      },
      onRebook: () => {
        if (detail?.booking_draft_id) {
          router.push(`/booking-drafts/${detail.booking_draft_id}`);
          return;
        }
        openBuilderFromDetail("Rebook order");
      },
      onCreateReturn: () => router.push(`/claims?order_id=${id}`),
      onGenerateInvoice: () => {
        void (async () => {
          try {
            const token = await getApiToken();
            const res = await ordersApi.generateInvoice(token, id);
            flashNotice(`Invoice ${res.invoice_number} ready.`);
            await invalidate();
          } catch (err) {
            flashError(err instanceof Error ? err.message : "Invoice generation failed");
          }
        })();
      },
      onResendReceipt: () => {
        void (async () => {
          try {
            const token = await getApiToken();
            const res = await ordersApi.resendReceipt(token, id);
            flashNotice(
              res.email
                ? `Receipt resent to ${res.email}`
                : "Receipt event queued (no recipient email on file)."
            );
            await invalidate();
          } catch (err) {
            flashError(err instanceof Error ? err.message : "Resend receipt failed");
          }
        })();
      },
      onRefund: () => {
        flashNotice("Refunds are processed through Finance — opening billing.");
        router.push("/finance");
      },
      onOpenClaim: () => router.push(`/claims?order_id=${id}`),
      onOpenSupport: () => router.push(`/support?order_id=${id}`),
      onShareTracking: () => {
        const url = `${window.location.origin}/track/${detail?.tracking_number ?? id}`;
        void navigator.clipboard.writeText(url).then(
          () => flashNotice("Tracking link copied."),
          () => flashError("Could not copy tracking link")
        );
      },
      onPrintLabels: () => {
        void (async () => {
          try {
            const token = await getApiToken();
            await downloadOrderFile(
              token,
              ordersApi.labelPdfUrl(id),
              `label-${detail?.tracking_number ?? id}.pdf`
            );
            flashNotice("Label PDF downloaded.");
          } catch (err) {
            flashError(err instanceof Error ? err.message : "Label PDF failed");
          }
        })();
      },
      onPrintManifest: () => {
        void (async () => {
          try {
            const token = await getApiToken();
            await downloadOrderFile(
              token,
              ordersApi.manifestPdfUrl(id),
              `manifest-${detail?.tracking_number ?? id}.pdf`
            );
            flashNotice("Manifest PDF downloaded.");
          } catch (err) {
            flashError(err instanceof Error ? err.message : "Manifest PDF failed");
          }
        })();
      },
      onDownloadRecord: () => {
        void (async () => {
          try {
            const token = await getApiToken();
            await downloadOrderFile(
              token,
              ordersApi.compliancePdfUrl(id),
              `shipment-${detail?.order_number ?? id}.pdf`
            );
            flashNotice("Shipment record downloaded.");
          } catch (err) {
            flashError(err instanceof Error ? err.message : "Shipment record failed");
          }
        })();
      },
    }),
    [detail, flashError, flashNotice, getApiToken, id, invalidate, openBuilderFromDetail, router]
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
        actionError={actionError}
        actionNotice={actionNotice}
        onRefresh={() => void invalidate()}
      />
      <AssignDriverModal
        open={assignOpen}
        orderId={id}
        trackingNumber={detail?.tracking_number}
        currentDriverName={detail?.driver_name}
        onClose={() => setAssignOpen(false)}
        onAssigned={() => {
          flashNotice("Driver assignment updated.");
          void invalidate();
        }}
      />
      <ExceptionReasonModal
        open={exceptionOpen}
        trackingNumber={detail?.tracking_number}
        initialColumn={exceptionInitial}
        onClose={() => setExceptionOpen(false)}
        onConfirm={async (column, reason) => {
          setActionError(null);
          try {
            const token = await getApiToken();
            await ops.moveBoardOrder(token, id, column, reason);
            flashNotice("Exception recorded.");
            await invalidate();
          } catch (e) {
            const message = e instanceof Error ? e.message : "Could not mark exception";
            flashError(message);
            throw e;
          }
        }}
      />
      <OrderBuilderModal
        open={builderOpen}
        prefill={builderPrefill}
        onClose={() => {
          setBuilderOpen(false);
          setBuilderPrefill(null);
        }}
        onCreated={(orderId) => {
          setBuilderOpen(false);
          setBuilderPrefill(null);
          router.push(`/orders/${orderId}`);
        }}
      />
    </>
  );
}
