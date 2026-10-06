import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import ReferralsClient from "@/components/referrals/ReferralsClient";
import { merchantOrgId, merchantServerFetch } from "@/lib/server-api";

export default async function ReferralsPage() {
  const orgId = await merchantOrgId();
  const client = new QueryClient();
  if (orgId) {
    const overview = await merchantServerFetch<unknown>("/v1/merchant/referrals", orgId);
    if (overview) client.setQueryData(["merchant-referrals", orgId], overview);
  }

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <ReferralsClient />
    </HydrationBoundary>
  );
}
