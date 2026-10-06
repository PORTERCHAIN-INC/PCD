import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import MerchantsListClient from "@/components/merchants/MerchantsListClient";
import { adminServerFetch } from "@/lib/server-api";

export default async function MerchantsPage() {
  const client = new QueryClient();
  const [list, stats] = await Promise.all([
    adminServerFetch<unknown>("/v1/admin/merchants?limit=500"),
    adminServerFetch<unknown>("/v1/admin/merchants/stats"),
  ]);
  if (list) client.setQueryData(["admin", "merchants-list", 0, "", ""], list);
  if (stats) client.setQueryData(["admin", "merchants-stats", 0], stats);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <MerchantsListClient />
    </HydrationBoundary>
  );
}
