import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import DriversListClient from "@/components/drivers/DriversListClient";
import { adminServerFetch } from "@/lib/server-api";

export default async function DriversPage() {
  const client = new QueryClient();
  const [list, stats] = await Promise.all([
    adminServerFetch<unknown>("/v1/admin/drivers?limit=500"),
    adminServerFetch<unknown>("/v1/admin/drivers/stats"),
  ]);
  if (list) client.setQueryData(["admin", "drivers-list", 0], list);
  if (stats) client.setQueryData(["admin", "drivers-stats", 0], stats);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <DriversListClient />
    </HydrationBoundary>
  );
}
