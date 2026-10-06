import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import PricingCenterClient from "@/components/pricing/PricingCenterClient";
import { adminServerFetch } from "@/lib/server-api";

export default async function PricingPage() {
  const client = new QueryClient();
  const merchants = await adminServerFetch<unknown>("/v1/admin/merchants?limit=100");
  if (merchants) client.setQueryData(["admin", "pricing-center-merchants"], merchants);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <PricingCenterClient />
    </HydrationBoundary>
  );
}
