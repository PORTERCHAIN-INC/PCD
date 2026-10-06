import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import { adminServerFetch } from "@/lib/server-api";
import BookingDraftDetailClient from "./booking-draft-detail-client";

export default async function BookingDraftDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const client = new QueryClient();
  const detail = await adminServerFetch<unknown>(`/v1/admin/booking-drafts/${id}`);
  if (detail) client.setQueryData(["booking-draft", id], detail);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <BookingDraftDetailClient id={id} />
    </HydrationBoundary>
  );
}
