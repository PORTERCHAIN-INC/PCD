import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import OrderDetailPageClient from "@/components/orders/OrderDetailPageClient";
import { adminServerFetch } from "@/lib/server-api";

type Props = { params: Promise<{ id: string }> };

export default async function OrderDetailPage({ params }: Props) {
  const { id } = await params;
  const client = new QueryClient();
  const [detail, tracking] = await Promise.all([
    adminServerFetch<unknown>(`/v1/admin/orders/${id}`),
    adminServerFetch<unknown>(`/v1/admin/orders/${id}/tracking`),
  ]);
  if (detail) client.setQueryData(["order", id], detail);
  if (tracking) client.setQueryData(["order-tracking", id], tracking);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <OrderDetailPageClient id={id} />
    </HydrationBoundary>
  );
}
