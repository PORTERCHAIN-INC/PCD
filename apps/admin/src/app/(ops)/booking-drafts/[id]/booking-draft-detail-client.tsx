"use client";

import dynamic from "next/dynamic";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { bookingDraftsApi } from "@/lib/booking-drafts";

const BookingDraftDetailView = dynamic(
  () => import("@/components/booking-drafts/BookingDraftDetailView"),
  { loading: () => <PageSkeleton rows={4} />, ssr: false }
);

export default function BookingDraftDetailClient({ id }: { id: string }) {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const qc = useQueryClient();

  const {
    data: detail,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["booking-draft", id],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => {
      const token = await getApiToken();
      return bookingDraftsApi.detail(token, id);
    },
  });

  async function action(fn: (token: string) => Promise<unknown>) {
    const token = await getApiToken();
    await fn(token);
    await qc.invalidateQueries({ queryKey: ["booking-draft", id] });
    await qc.invalidateQueries({ queryKey: ["booking-drafts"] });
    void refetch();
  }

  return (
    <BookingDraftDetailView
      detail={detail ?? null}
      loading={isLoading && !detail}
      actionLoading={false}
      onExtend={() => void action((t) => bookingDraftsApi.extend(t, id))}
      onCancel={() => {
        if (!confirm("Cancel this booking draft?")) return;
        void action((t) => bookingDraftsApi.cancel(t, id, "Cancelled by admin"));
      }}
      onRestore={() => void action((t) => bookingDraftsApi.restore(t, id))}
      onExpire={() => void action((t) => bookingDraftsApi.expire(t, id))}
      onDuplicate={() => void action((t) => bookingDraftsApi.duplicate(t, id))}
      onSendPaymentLink={async () => {
        const token = await getApiToken();
        const res = await bookingDraftsApi.sendPaymentLink(token, id);
        if (res.checkout_url) window.open(res.checkout_url, "_blank", "noopener,noreferrer");
        else alert("Payment link created — check Stripe mock or customer email flow");
        void refetch();
      }}
    />
  );
}
