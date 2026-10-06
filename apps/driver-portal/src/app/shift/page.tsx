import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import ShiftClient from "@/components/shift/ShiftClient";
import { driverServerGet } from "@/lib/server-api";

export default async function ShiftPage() {
  const client = new QueryClient();
  const shift = await driverServerGet<unknown>("/v1/shift");
  if (shift) client.setQueryData(["driver-shift"], shift);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <ShiftClient />
    </HydrationBoundary>
  );
}
