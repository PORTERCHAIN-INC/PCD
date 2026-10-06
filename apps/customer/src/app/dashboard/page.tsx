import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import CustomerDashboardClient from "./dashboard-client";
import { customerServerFetch } from "@/lib/server-api";

export default async function DashboardPage() {
  const client = new QueryClient();
  const dashboard = await customerServerFetch<unknown>("/v1/customers/me/dashboard");
  if (dashboard) {
    client.setQueryData(["customer-dashboard"], dashboard);
  }

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <CustomerDashboardClient />
    </HydrationBoundary>
  );
}
