import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import AdminShell from "@/components/AdminShell";
import AdminQueryProvider from "@/components/providers/AdminQueryProvider";
import { AdminProfileProvider } from "@/components/nav/AdminProfileContext";
import { adminServerFetch } from "@/lib/server-api";

export default async function PortalLayout({ children }: { children: React.ReactNode }) {
  const client = new QueryClient();
  const inbox = await adminServerFetch<unknown>("/v1/notifications/inbox?limit=20");
  if (inbox) client.setQueryData(["admin-notification-inbox"], inbox);

  return (
    <AdminQueryProvider>
      <HydrationBoundary state={dehydrate(client)}>
        <AdminProfileProvider>
          <AdminShell>{children}</AdminShell>
        </AdminProfileProvider>
      </HydrationBoundary>
    </AdminQueryProvider>
  );
}
