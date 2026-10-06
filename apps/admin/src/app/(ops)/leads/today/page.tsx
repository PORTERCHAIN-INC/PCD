import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import LeadsTodayClient from "@/components/leads/LeadsTodayClient";
import { adminServerFetch } from "@/lib/server-api";

export default async function LeadsTodayPage() {
  const client = new QueryClient();
  const today = await adminServerFetch<unknown>("/v1/admin/leads/today");
  if (today) client.setQueryData(["leads-today"], today);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <LeadsTodayClient />
    </HydrationBoundary>
  );
}
