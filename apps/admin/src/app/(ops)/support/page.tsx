import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import SupportListClient from "@/components/support/SupportListClient";
import { adminServerFetch } from "@/lib/server-api";

export default async function SupportPage() {
  const client = new QueryClient();
  const tickets = await adminServerFetch<unknown>("/v1/admin/support/tickets");
  if (tickets)
    client.setQueryData(["support-tickets", JSON.stringify({ tab: "tickets" })], tickets);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <SupportListClient />
    </HydrationBoundary>
  );
}
