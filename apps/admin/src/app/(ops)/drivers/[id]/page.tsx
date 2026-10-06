import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import DriverDetailClient from "@/components/drivers/DriverDetailClient";
import { adminServerFetch } from "@/lib/server-api";

type Props = { params: Promise<{ id: string }> };

export default async function DriverDetailPage({ params }: Props) {
  const { id } = await params;
  const client = new QueryClient();
  const detail = await adminServerFetch<unknown>(`/v1/admin/drivers/${id}`);
  if (detail) client.setQueryData(["admin", `driver-detail-${id}`, id, 0], detail);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <DriverDetailClient id={id} />
    </HydrationBoundary>
  );
}
