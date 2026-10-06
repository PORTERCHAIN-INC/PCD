import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import LeadsListClient from "@/components/leads/LeadsListClient";
import { buildLeadFiltersQuery } from "@/lib/leads";
import { adminServerFetch } from "@/lib/server-api";

export default async function LeadsPage() {
  const client = new QueryClient();
  const query = buildLeadFiltersQuery({ sort: "smart", limit: 50, offset: 0 });
  const page = await adminServerFetch<unknown>(`/v1/admin/leads${query}`);
  if (page) client.setQueryData(["leads", JSON.stringify({ sort: "smart" })], page);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <LeadsListClient />
    </HydrationBoundary>
  );
}
