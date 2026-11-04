"use client";

import { useCallback, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { NotificationBell as Bell } from "@porterchain/ui/notification-bell";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useAdminNotificationRealtime } from "@/hooks/useAdminNotificationRealtime";
import { adminFetch } from "@/lib/api";

type InboxItem = {
  id: string;
  title: string;
  body: string;
  priority: string;
  category: string;
  deep_link?: string | null;
  is_read: boolean;
  created_at: string;
};

type InboxPayload = {
  unread_count: number;
  items: InboxItem[];
};

async function loadInbox(token: string): Promise<InboxPayload> {
  return adminFetch<InboxPayload>("/v1/notifications/inbox?limit=20", token);
}

export default function NotificationBell({
  viewAllHref = "/notifications",
}: {
  viewAllHref?: string;
}) {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const qc = useQueryClient();
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");
  /** WS is deferred until idle / first open — Query poll covers the gap. */
  const [wsArmed, setWsArmed] = useState(false);

  useEffect(() => {
    if (!enabled || wsArmed) return;
    let idleId: number | undefined;
    let timeoutId: ReturnType<typeof setTimeout> | undefined;
    const arm = () => setWsArmed(true);
    if (typeof window !== "undefined" && "requestIdleCallback" in window) {
      idleId = window.requestIdleCallback(arm, { timeout: 4000 });
    } else {
      timeoutId = setTimeout(arm, 2500);
    }
    return () => {
      if (idleId !== undefined && "cancelIdleCallback" in window) {
        window.cancelIdleCallback(idleId);
      }
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [enabled, wsArmed]);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-notification-inbox"],
    enabled,
    queryFn: async () => loadInbox(await getApiToken()),
  });

  useAdminNotificationRealtime(enabled && wsArmed, getApiToken, () => {
    void qc.invalidateQueries({ queryKey: ["admin-notification-inbox"] });
  });

  const unread = data?.unread_count ?? 0;
  const items = data?.items ?? [];

  const markRead = useCallback(
    async (id: string) => {
      const token = await getApiToken();
      await adminFetch(`/v1/notifications/inbox/${id}/read`, token, { method: "POST" });
      await qc.invalidateQueries({ queryKey: ["admin-notification-inbox"] });
    },
    [getApiToken, qc]
  );

  const markAll = useCallback(async () => {
    const token = await getApiToken();
    await adminFetch(`/v1/notifications/inbox/mark-all-read`, token, { method: "POST" });
    await qc.invalidateQueries({ queryKey: ["admin-notification-inbox"] });
  }, [getApiToken, qc]);

  return (
    <Bell
      variant="ops"
      items={items}
      unread={unread}
      loading={isLoading}
      viewAllHref={viewAllHref}
      emptyHint="Tickets, claims, and ops show up here. Leads stay in Lead Agent."
      onTriggerClick={() => setWsArmed(true)}
      onMarkRead={markRead}
      onMarkAll={markAll}
    />
  );
}
