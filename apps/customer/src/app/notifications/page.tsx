import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import NotificationsClient from "@/components/notifications/NotificationsClient";
import { customerServerFetch } from "@/lib/server-api";

export default async function CustomerNotificationsPage() {
  const client = new QueryClient();
  const inbox = await customerServerFetch<unknown>("/v1/notifications/inbox?limit=100");
  if (inbox) client.setQueryData(["customer-notification-inbox"], inbox);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <NotificationsClient />
    </HydrationBoundary>
  );
}
