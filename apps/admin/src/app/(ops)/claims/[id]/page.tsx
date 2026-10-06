import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import ClaimDetailClient from "./claim-detail-client";
import { adminServerFetch } from "@/lib/server-api";

type Props = { params: Promise<{ id: string }> };

export default async function ClaimDetailPage({ params }: Props) {
  const { id } = await params;
  const client = new QueryClient();
  const detail = await adminServerFetch<unknown>(`/v1/admin/claims/${id}`);
  if (detail) client.setQueryData(["claim", id], detail);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <ClaimDetailClient id={id} />
    </HydrationBoundary>
  );
}
