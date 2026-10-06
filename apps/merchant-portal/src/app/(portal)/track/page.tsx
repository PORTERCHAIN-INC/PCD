import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import TrackPageClient from "@/components/tracking/TrackPageClient";
import { merchantOrgId, merchantServerFetch } from "@/lib/server-api";

export default async function TrackPage() {
  const orgId = await merchantOrgId();
  const keyOrg = orgId ?? null;
  const client = new QueryClient();
  const dashboard = await merchantServerFetch<unknown>("/v1/merchant/tracking/dashboard", orgId);
  if (dashboard) {
    client.setQueryData(["merchant-tracking-dashboard", keyOrg], dashboard);
  }

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <TrackPageClient />
    </HydrationBoundary>
  );
}
