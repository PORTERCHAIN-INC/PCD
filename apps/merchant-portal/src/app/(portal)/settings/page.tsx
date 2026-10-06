import { Suspense } from "react";
import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import { PageSkeleton, RouteLoading } from "@porterchain/ui/loading";
import SettingsClient from "@/components/settings/SettingsClient";
import { merchantOrgId, merchantServerFetch } from "@/lib/server-api";

export default async function SettingsPage() {
  const orgId = await merchantOrgId();
  const client = new QueryClient();
  const overview = await merchantServerFetch<unknown>("/v1/merchant/settings/overview", orgId);
  if (overview) {
    client.setQueryData(["merchant-settings-overview", orgId ?? null], overview);
  }

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <Suspense
        fallback={
          <RouteLoading label="Loading settings">
            <PageSkeleton rows={5} />
          </RouteLoading>
        }
      >
        <SettingsClient />
      </Suspense>
    </HydrationBoundary>
  );
}
