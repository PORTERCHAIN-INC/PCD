import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import SupportDetailClient from "./support-detail-client";
import { adminServerFetch } from "@/lib/server-api";

type Props = { params: Promise<{ id: string }> };

export default async function SupportDetailPage({ params }: Props) {
  const { id } = await params;
  const client = new QueryClient();
  const detail = await adminServerFetch<unknown>(`/v1/admin/support/tickets/${id}`);
  if (detail) client.setQueryData(["support-ticket", id], detail);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <SupportDetailClient id={id} />
    </HydrationBoundary>
  );
}
