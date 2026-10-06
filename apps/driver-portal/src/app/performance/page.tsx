import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import { driverServerGet } from "@/lib/server-api";
import type { DriverPerformance } from "@/lib/api";
import PerformanceClient from "./performance-client";

export default async function PerformancePage() {
  const client = new QueryClient();
  const data = await driverServerGet<DriverPerformance>("/v1/performance");
  if (data) client.setQueryData(["driver-performance"], data);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <PerformanceClient />
    </HydrationBoundary>
  );
}
