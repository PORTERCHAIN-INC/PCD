import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import NotificationsCenterClient from "@/components/notifications/NotificationsCenterClient";
import { adminServerFetch } from "@/lib/server-api";

export default async function NotificationsPage() {
  const client = new QueryClient();
  const inbox = await adminServerFetch<unknown>(
    "/v1/notifications/inbox?limit=100&exclude=lead_sla_escalation"
  );
  if (inbox) client.setQueryData(["admin-notification-center-inbox"], inbox);

  return (
    <HydrationBoundary state={dehydrate(client)}>
      <NotificationsCenterClient />
    </HydrationBoundary>
  );
}
