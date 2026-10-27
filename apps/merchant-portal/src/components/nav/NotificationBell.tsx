"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { NotificationBell as Bell } from "@porterchain/ui/notification-bell";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { notificationsApi } from "@/lib/notifications";

export default function NotificationBell({
  viewAllHref = "/notifications",
}: {
  viewAllHref?: string;
}) {
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const qc = useQueryClient();
  const enabled = Boolean(isLoaded && isSignedIn && orgId);
  const key = ["merchant-notification-inbox", orgId];

  const { data, isLoading } = useQuery({
    queryKey: key,
    enabled,
    staleTime: 30_000,
    queryFn: async () => notificationsApi.inbox(await getApiToken(), orgId, 20),
  });

  if (isLoaded && !isSignedIn) return null;
  if (!data && !isSignedIn) return null;

  return (
    <Bell
      items={data?.items ?? []}
      unread={data?.unread_count ?? 0}
      loading={isLoading}
      viewAllHref={viewAllHref}
      showUnreadCount={false}
      onMarkRead={async (id) => {
        await notificationsApi.markRead(await getApiToken(), id, orgId);
        await qc.invalidateQueries({ queryKey: key });
      }}
      onMarkAll={async () => {
        await notificationsApi.markAllRead(await getApiToken(), orgId);
        await qc.invalidateQueries({ queryKey: key });
      }}
    />
  );
}
