import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import DashboardClient from "./DashboardClient";
import { merchantOrgId, merchantServerFetch } from "@/lib/server-api";

export default async function DashboardPage() {
  const orgId = await merchantOrgId();
  const client = new QueryClient();
  const dashboard = await merchantServerFetch<unknown>("/v1/merchant/dashboard", orgId);
  if (dashboard) {
    client.setQueryData(["merchant-dashboard", orgId ?? null], dashboard);
  }

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <DashboardClient />
    </HydrationBoundary>
  );
}
