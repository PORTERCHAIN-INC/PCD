import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import ReportsClient from "@/components/reports/ReportsClient";
import { merchantOrgId, merchantServerFetch } from "@/lib/server-api";

export default async function ReportsPage() {
  const orgId = await merchantOrgId();
  const client = new QueryClient();
  if (orgId) {
    const [overview, saved] = await Promise.all([
      merchantServerFetch<unknown>("/v1/merchant/reports/overview", orgId),
      merchantServerFetch<unknown>("/v1/merchant/reports/saved", orgId),
    ]);
    if (overview) client.setQueryData(["merchant-reports-overview", orgId], overview);
    if (saved) client.setQueryData(["merchant-reports-saved", orgId], saved);
  }

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <ReportsClient />
    </HydrationBoundary>
  );
}
