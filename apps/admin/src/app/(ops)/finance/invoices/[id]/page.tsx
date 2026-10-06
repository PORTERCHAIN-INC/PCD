import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import FinanceInvoiceClient from "./invoice-client";
import { adminServerFetch } from "@/lib/server-api";

type Props = { params: Promise<{ id: string }> };

export default async function FinanceInvoicePage({ params }: Props) {
  const { id } = await params;
  const client = new QueryClient();
  const detail = await adminServerFetch<unknown>(`/v1/admin/finance/invoices/${id}`);
  if (detail) client.setQueryData(["finance-invoice", id], detail);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <FinanceInvoiceClient id={id} />
    </HydrationBoundary>
  );
}
