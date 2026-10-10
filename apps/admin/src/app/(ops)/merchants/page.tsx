import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import MerchantBoardClient from "@/components/merchants/MerchantBoardClient";
import MerchantsListClient from "@/components/merchants/MerchantsListClient";
import { adminServerFetch } from "@/lib/server-api";

/** Board (Needs action / All, paged) by default; ?mode=table keeps the classic table, CSV and signups. */
export default async function MerchantsPage({
  searchParams,
}: {
  searchParams: Promise<{ mode?: string }>;
}) {
  const { mode } = await searchParams;
  if (mode !== "table") return <MerchantBoardClient />;

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
