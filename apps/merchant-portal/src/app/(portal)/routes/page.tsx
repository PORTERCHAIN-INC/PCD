import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import { merchantOrgId, merchantServerFetch } from "@/lib/server-api";
import RoutesClient from "./routes-client";

/** Default list filters match RouteList initial state (scope=all, no filters). */
export default async function RoutesPage() {
  const orgId = await merchantOrgId();
  const keyOrg = orgId ?? null;
  const client = new QueryClient();
  const list = await merchantServerFetch<{
    total: number;
    today: number;
    construction: number;
    routes: unknown[];
  }>("/v1/merchant/route-imports", orgId);
  if (list) {
    client.setQueryData(["merchant-routes", keyOrg, "all", "", false, "", "", "", 0], list);
  }

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <RoutesClient />
    </HydrationBoundary>
  );
}
