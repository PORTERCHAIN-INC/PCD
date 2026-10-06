import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import DashboardClient from "@/components/dashboard/DashboardClient";
import { adminServerFetch } from "@/lib/server-api";

export default async function DashboardPage() {
  const client = new QueryClient();
  const center = await adminServerFetch<unknown>("/v1/admin/dashboard/center");
  if (center) {
    client.setQueryData(["dashboard-center"], center);
  }

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <DashboardClient />
    </HydrationBoundary>
  );
}
