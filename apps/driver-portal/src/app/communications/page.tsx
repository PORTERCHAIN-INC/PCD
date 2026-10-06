import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import CommunicationsClient from "@/components/communications/CommunicationsClient";
import type { DriverCommunicationsSnapshot } from "@/lib/communications";
import { driverServerGet } from "@/lib/server-api";

export default async function CommunicationsPage() {
  const client = new QueryClient();
  const snap = await driverServerGet<DriverCommunicationsSnapshot>("/v1/communications");
  if (snap) client.setQueryData(["driver-communications"], snap);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <CommunicationsClient />
    </HydrationBoundary>
  );
}
