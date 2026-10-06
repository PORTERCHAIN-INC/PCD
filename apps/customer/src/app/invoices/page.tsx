import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import InvoicesClient from "@/components/invoices/InvoicesClient";
import { customerServerFetch } from "@/lib/server-api";

export default async function InvoicesPage() {
  const client = new QueryClient();
  const rows = await customerServerFetch<unknown>("/v1/customers/me/invoices");
  if (rows) client.setQueryData(["customer-invoices"], rows);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <InvoicesClient />
    </HydrationBoundary>
  );
}
