import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import { merchantOrgId, merchantServerFetch } from "@/lib/server-api";
import OrderDetailClient from "./order-detail-client";

export default async function OrderDetailPage({
  params,
}: {
  params: Promise<{ order_id: string }>;
}) {
  const { order_id } = await params;
  const orgId = await merchantOrgId();
  const keyOrg = orgId ?? null;
  const client = new QueryClient();
  const [detail, tracking] = await Promise.all([
    merchantServerFetch<unknown>(`/v1/merchant/orders/${order_id}/360`, orgId),
    merchantServerFetch<unknown>(`/v1/merchant/orders/${order_id}/tracking`, orgId),
  ]);
  if (detail) client.setQueryData(["merchant-order-360", keyOrg, order_id], detail);
  if (tracking) client.setQueryData(["merchant-order-tracking", keyOrg, order_id], tracking);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <OrderDetailClient orderId={order_id} />
    </HydrationBoundary>
  );
}
