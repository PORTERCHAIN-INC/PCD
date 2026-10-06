import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import JobDetailClient from "./job-detail-client";
import { driverServerGet } from "@/lib/server-api";

type Props = { params: Promise<{ orderId: string }> };

export default async function JobDetailPage({ params }: Props) {
  const { orderId } = await params;
  const client = new QueryClient();
  const job = await driverServerGet<unknown>(`/v1/jobs/${orderId}`);
  if (job) client.setQueryData(["driver-job", orderId], job);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <JobDetailClient orderId={orderId} />
    </HydrationBoundary>
  );
}
