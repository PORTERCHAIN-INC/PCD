import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import InvoiceDetailClient from "@/components/invoices/InvoiceDetailClient";
import { customerServerFetch } from "@/lib/server-api";

type Props = { params: Promise<{ invoice_id: string }> };

export default async function InvoiceDetailPage({ params }: Props) {
  const { invoice_id } = await params;
  const client = new QueryClient();
  const detail = await customerServerFetch<unknown>(`/v1/customers/me/invoices/${invoice_id}`);
  if (detail) client.setQueryData(["customer-invoice", invoice_id], detail);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <InvoiceDetailClient invoiceId={invoice_id} />
    </HydrationBoundary>
  );
}
