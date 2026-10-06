import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import LeadDetailClient from "@/components/leads/LeadDetailClient";
import { adminServerFetch } from "@/lib/server-api";

type Props = { params: Promise<{ id: string }> };

export default async function LeadDetailPage({ params }: Props) {
  const { id } = await params;
  const client = new QueryClient();
  const lead = await adminServerFetch<unknown>(`/v1/admin/leads/${id}`);
  if (lead) client.setQueryData(["lead", id], lead);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <LeadDetailClient params={params} />
    </HydrationBoundary>
  );
}
