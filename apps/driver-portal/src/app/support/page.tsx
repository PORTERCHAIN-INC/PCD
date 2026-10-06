import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import DriverSupportClient from "@/components/support/DriverSupportClient";
import { driverServerGet } from "@/lib/server-api";

export default async function SupportPage() {
  const client = new QueryClient();
  const hub = await driverServerGet<unknown>("/v1/support/hub");
  if (hub) client.setQueryData(["driver-support-hub"], hub);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <DriverSupportClient />
    </HydrationBoundary>
  );
}
