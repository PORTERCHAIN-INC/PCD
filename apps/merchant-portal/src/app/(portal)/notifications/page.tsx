import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import NotificationsPageClient from "@/components/notifications/NotificationsPageClient";
import { merchantOrgId, merchantServerFetch } from "@/lib/server-api";

export default async function MerchantNotificationsPage() {
  const orgId = await merchantOrgId();
  const client = new QueryClient();
  if (orgId) {
    const inbox = await merchantServerFetch<unknown>("/v1/notifications/inbox?limit=100", orgId);
    if (inbox) client.setQueryData(["merchant-notification-inbox", orgId], inbox);
  }

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <NotificationsPageClient />
    </HydrationBoundary>
  );
}
