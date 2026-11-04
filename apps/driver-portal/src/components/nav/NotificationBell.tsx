"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { NotificationBell as Bell } from "@porterchain/ui/notification-bell";
import { driverApi } from "@/lib/api";

const KEY = ["driver-notification-inbox"];

export default function NotificationBell({
  viewAllHref = "/communications",
}: {
  viewAllHref?: string;
}) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: KEY,
    staleTime: 20_000,
    queryFn: async () => {
      const snap = await driverApi.communicationsHub();
      return {
        items: snap.notifications.items.slice(0, 20),
        unread: snap.notifications.unread_count,
      };
    },
  });

  return (
    <Bell
      items={data?.items ?? []}
      unread={data?.unread ?? 0}
      loading={isLoading}
      viewAllHref={viewAllHref}
      onMarkRead={async (id) => {
        await driverApi.markNotificationRead(id);
        await qc.invalidateQueries({ queryKey: KEY });
      }}
      onMarkAll={async () => {
        await driverApi.markAllNotificationsRead();
        await qc.invalidateQueries({ queryKey: KEY });
      }}
    />
  );
}
