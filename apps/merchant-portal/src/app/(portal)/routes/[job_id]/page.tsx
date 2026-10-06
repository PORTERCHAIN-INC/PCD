import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import RouteJobDetail from "@/components/routes/RouteJobDetail";
import { merchantOrgId, merchantServerFetch } from "@/lib/server-api";

export default async function RouteJobPage({ params }: { params: Promise<{ job_id: string }> }) {
  const { job_id } = await params;
  const orgId = await merchantOrgId();
  const keyOrg = orgId ?? null;
  const client = new QueryClient();
  const job = await merchantServerFetch<unknown>(`/v1/merchant/route-imports/${job_id}`, orgId);
  if (job) client.setQueryData(["merchant-route-job", keyOrg, job_id], job);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <RouteJobDetail jobId={job_id} />
    </HydrationBoundary>
  );
}
