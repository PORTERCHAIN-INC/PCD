import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import CustomersScreen from "./screen";
import { adminServerFetch } from "@/lib/server-api";

export default async function CustomersPage() {
  const client = new QueryClient();
  const [list, stats] = await Promise.all([
    adminServerFetch<unknown>("/v1/admin/customers"),
    adminServerFetch<unknown>("/v1/admin/customers/stats"),
  ]);
  if (list) client.setQueryData(["admin", "customers-{}-0", 0], list);
  if (stats) client.setQueryData(["admin", "customers-stats-0", 0], stats);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <CustomersScreen />
    </HydrationBoundary>
  );
}
