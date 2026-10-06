import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import BookingDraftsListClient from "@/components/booking-drafts/BookingDraftsListClient";
import { adminServerFetch } from "@/lib/server-api";

export default async function BookingDraftsPage() {
  const client = new QueryClient();
  const [rows, analytics] = await Promise.all([
    adminServerFetch<unknown>("/v1/admin/booking-drafts"),
    adminServerFetch<unknown>("/v1/admin/booking-drafts/analytics"),
  ]);
  if (rows) client.setQueryData(["booking-drafts", "{}"], rows);
  if (analytics) client.setQueryData(["booking-drafts-analytics"], analytics);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <BookingDraftsListClient />
    </HydrationBoundary>
  );
}
