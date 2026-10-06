import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import MerchantDetailClient from "@/components/merchants/MerchantDetailClient";
import { adminServerFetch } from "@/lib/server-api";

type Props = { params: Promise<{ id: string }> };

export default async function MerchantDetailPage({ params }: Props) {
  const { id } = await params;
  const client = new QueryClient();
  const detail = await adminServerFetch<unknown>(`/v1/admin/merchants/${id}`);
  if (detail) client.setQueryData(["admin", `merchant-detail-${id}`, id, 0], detail);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <MerchantDetailClient id={id} />
    </HydrationBoundary>
  );
}
