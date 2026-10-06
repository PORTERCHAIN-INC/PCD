import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import { customerServerFetch } from "@/lib/server-api";
import TrackOrderClient from "./track-order-client";

export default async function TrackOrderPage({
  params,
}: {
  params: Promise<{ trackingNumber: string }>;
}) {
  const { trackingNumber } = await params;
  const client = new QueryClient();
  const [order, live] = await Promise.all([
    customerServerFetch<unknown>(`/v1/orders/${encodeURIComponent(trackingNumber)}`),
    customerServerFetch<unknown>(`/v1/orders/${encodeURIComponent(trackingNumber)}/tracking`),
  ]);
  if (order) client.setQueryData(["customer-track-order", trackingNumber], order);
  if (live) client.setQueryData(["customer-track-live", trackingNumber], live);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <TrackOrderClient trackingNumber={trackingNumber} />
    </HydrationBoundary>
  );
}
