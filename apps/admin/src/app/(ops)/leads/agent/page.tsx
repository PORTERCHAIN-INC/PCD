import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import LeadsAgentClient from "@/components/leads/LeadsAgentClient";
import { adminServerFetch } from "@/lib/server-api";

export default async function LeadsAgentPage() {
  const client = new QueryClient();
  const activity = await adminServerFetch<unknown>("/v1/admin/leads/agent");
  if (activity) client.setQueryData(["leads-agent-activity"], activity);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <LeadsAgentClient />
    </HydrationBoundary>
  );
}
