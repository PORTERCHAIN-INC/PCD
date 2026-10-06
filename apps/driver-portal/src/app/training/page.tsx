import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import { driverServerGet } from "@/lib/server-api";
import TrainingClient from "./training-client";

export default async function TrainingPage() {
  const client = new QueryClient();
  const data = await driverServerGet<{ modules: unknown[] }>("/v1/training");
  if (data) client.setQueryData(["driver-training"], data);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <TrainingClient />
    </HydrationBoundary>
  );
}
