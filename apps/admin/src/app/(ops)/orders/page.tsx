import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import OrdersScreen from "./screen";
import { adminServerFetch } from "@/lib/server-api";
import { boardQuery } from "@/lib/orderBoard";
import { ORDER_PAGE_SIZE } from "@/lib/orders";

function queryString(filters: Record<string, string | number | boolean | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export default async function OrdersPage() {
  const board = boardQuery("today", "needs_decision", "", "", undefined);
  const filterKey = JSON.stringify({ ...board, period: "today" });
  const listFilters = { ...board, limit: ORDER_PAGE_SIZE, offset: 0 };
  const client = new QueryClient();
  const [page, dashboard] = await Promise.all([
    adminServerFetch<unknown>(`/v1/admin/orders${queryString(listFilters)}`),
    adminServerFetch<unknown>("/v1/admin/orders/dashboard"),
  ]);
  if (page) client.setQueryData(["orders", filterKey, 0], page);
  if (dashboard) client.setQueryData(["orders-dashboard"], dashboard);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <OrdersScreen />
    </HydrationBoundary>
  );
}
