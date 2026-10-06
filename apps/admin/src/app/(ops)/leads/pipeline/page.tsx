import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import LeadsPipelineClient from "@/components/leads/LeadsPipelineClient";
import { adminServerFetch } from "@/lib/server-api";

export default async function LeadsPipelinePage() {
  const client = new QueryClient();
  const columns = await adminServerFetch<unknown>("/v1/admin/leads/pipeline");
  if (columns) client.setQueryData(["leads-pipeline", ""], columns);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <LeadsPipelineClient />
    </HydrationBoundary>
  );
}
