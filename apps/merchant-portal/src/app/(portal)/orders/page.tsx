import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import OrdersListClient from "@/components/orders/OrdersListClient";
import { ORDER_PAGE_SIZE } from "@/lib/orders";
import { merchantOrgId, merchantServerFetch } from "@/lib/server-api";

export default async function OrdersPage() {
  const orgId = await merchantOrgId();
  const client = new QueryClient();
  const listPath = `/v1/merchant/orders?limit=${ORDER_PAGE_SIZE}&offset=0`;
  const [page, dashboard] = await Promise.all([
    merchantServerFetch<unknown>(listPath, orgId),
    merchantServerFetch<unknown>("/v1/merchant/orders/dashboard", orgId),
  ]);
  const keyOrg = orgId ?? null;
  if (page) client.setQueryData(["merchant-orders", keyOrg, {}, 0], page);
  if (dashboard) client.setQueryData(["merchant-orders-dashboard", keyOrg], dashboard);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <OrdersListClient />
    </HydrationBoundary>
  );
}
