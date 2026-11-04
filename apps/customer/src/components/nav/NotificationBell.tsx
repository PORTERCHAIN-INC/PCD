"use client";

import { useEffect } from "react";
import { useAuth } from "@porterchain/auth/oidc/client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { NotificationBell as Bell } from "@porterchain/ui/notification-bell";
import { isAuthConfigured, publicEnv } from "@/lib/env";
import { notificationsApi } from "@/lib/notifications";

export default function NotificationBell({
  viewAllHref = "/notifications",
}: {
  viewAllHref?: string;
}) {
  if (!isAuthConfigured()) return null;
  return <NotificationBellWithAuth viewAllHref={viewAllHref} />;
}

function NotificationBellWithAuth({ viewAllHref }: { viewAllHref: string }) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const qc = useQueryClient();
  const enabled = Boolean(isLoaded && isSignedIn);

  useEffect(() => {
    if (!enabled) return;
    let ws: WebSocket | null = null;
    let cancelled = false;
    void (async () => {
      const token = await getToken();
      if (!token || cancelled) return;
      const base = publicEnv.porterchainApiUrl.replace(/^http/, "ws");
      ws = new WebSocket(
        `${base}/v1/notifications/ws?token=${encodeURIComponent(token)}&portal=customer`
      );
      ws.onmessage = () => {
        void qc.invalidateQueries({ queryKey: ["customer-notification-inbox"] });
      };
    })();
    return () => {
      cancelled = true;
      ws?.close();
    };
  }, [enabled, getToken, qc]);

  const { data, isLoading: loading } = useQuery({
    queryKey: ["customer-notification-inbox"],
    enabled,
    staleTime: 30_000,
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("Not authenticated");
      return notificationsApi.inbox(token, 20);
    },
  });

  if (isLoaded && !isSignedIn) return null;
  if (!data && !isSignedIn) return null;

  return (
    <Bell
      items={data?.items ?? []}
      unread={data?.unread_count ?? 0}
      loading={loading}
      viewAllHref={viewAllHref}
      onMarkRead={async (id) => {
        const token = await getToken();
        if (token) await notificationsApi.markRead(token, id);
        await qc.invalidateQueries({ queryKey: ["customer-notification-inbox"] });
      }}
      onMarkAll={async () => {
        const token = await getToken();
        if (!token) return;
        await notificationsApi.markAllRead(token);
        await qc.invalidateQueries({ queryKey: ["customer-notification-inbox"] });
      }}
    />
  );
}
