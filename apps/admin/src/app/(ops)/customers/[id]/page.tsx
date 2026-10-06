import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import CustomerDetailClient from "@/components/customers/CustomerDetailClient";
import { adminServerFetch } from "@/lib/server-api";

type Props = { params: Promise<{ id: string }> };

export default async function CustomerDetailPage({ params }: Props) {
  const { id } = await params;
  const client = new QueryClient();
  const detail = await adminServerFetch<unknown>(`/v1/admin/customers/${id}`);
  if (detail) client.setQueryData(["admin", `customer-${id}-0`, id, 0], detail);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <CustomerDetailClient id={id} />
    </HydrationBoundary>
  );
}
