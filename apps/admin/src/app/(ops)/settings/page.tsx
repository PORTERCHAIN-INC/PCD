import { Suspense } from "react";
import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import { PageSkeleton, RouteLoading } from "@porterchain/ui/loading";
import SettingsCenter from "@/components/settings/SettingsCenter";
import { adminServerFetch } from "@/lib/server-api";

export default async function SettingsPage() {
  const client = new QueryClient();
  const center = await adminServerFetch<unknown>("/v1/admin/settings/center");
  if (center) {
    client.setQueryData(["settings-center"], center);
  }

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <Suspense
        fallback={
          <RouteLoading label="Loading settings">
            <PageSkeleton rows={6} />
          </RouteLoading>
        }
      >
        <SettingsCenter />
      </Suspense>
    </HydrationBoundary>
  );
}
