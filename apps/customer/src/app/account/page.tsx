import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import AccountClient from "@/components/account/AccountClient";
import { customerServerFetch } from "@/lib/server-api";

export default async function AccountPage() {
  const client = new QueryClient();
  const tickets = await customerServerFetch<unknown>("/v1/customers/me/support");
  if (tickets) client.setQueryData(["customer-support-tickets"], tickets);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <AccountClient />
    </HydrationBoundary>
  );
}
