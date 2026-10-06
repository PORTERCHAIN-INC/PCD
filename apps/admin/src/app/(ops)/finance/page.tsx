import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import FinanceCenterClient from "@/components/finance/FinanceCenterClient";
import { adminServerFetch } from "@/lib/server-api";

export default async function FinancePage() {
  const client = new QueryClient();
  const dashboard = await adminServerFetch<unknown>("/v1/admin/finance/dashboard");
  if (dashboard) client.setQueryData(["finance-dashboard"], dashboard);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <FinanceCenterClient />
    </HydrationBoundary>
  );
}
