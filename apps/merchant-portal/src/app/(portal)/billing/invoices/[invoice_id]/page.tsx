import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import InvoiceDetailClient from "@/components/billing/InvoiceDetailClient";
import { merchantOrgId, merchantServerFetch } from "@/lib/server-api";

type Props = { params: Promise<{ invoice_id: string }> };

export default async function InvoiceDetailPage({ params }: Props) {
  const { invoice_id } = await params;
  const orgId = await merchantOrgId();
  const client = new QueryClient();
  if (orgId) {
    const detail = await merchantServerFetch<unknown>(
      `/v1/merchant/billing/invoices/${invoice_id}`,
      orgId
    );
    if (detail) client.setQueryData(["merchant-invoice", orgId, invoice_id], detail);
  }

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <InvoiceDetailClient invoiceId={invoice_id} />
    </HydrationBoundary>
  );
}
