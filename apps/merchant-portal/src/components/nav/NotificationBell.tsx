"use client";

import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell } from "lucide-react";
import { cn } from "@/lib/utils";
import HeaderDropdown from "@/components/nav/HeaderDropdown";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { notificationsApi } from "@/lib/notifications";

function relativeTime(iso: string): string {
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return "";
  const mins = Math.round((Date.now() - t) / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.round(mins / 60);
  if (hrs < 48) return `${hrs}h`;
  return `${Math.round(hrs / 24)}d`;
}

export default function NotificationBell({
  viewAllHref = "/notifications",
}: {
  viewAllHref?: string;
}) {
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const qc = useQueryClient();
  const enabled = Boolean(isLoaded && isSignedIn && orgId);

  const { data, isLoading: loading } = useQuery({
    queryKey: ["merchant-notification-inbox", orgId],
    enabled,
    staleTime: 30_000,
    queryFn: async () => notificationsApi.inbox(await getApiToken(), orgId, 20),
  });

  const items = data?.items ?? [];
  const unread = data?.unread_count ?? 0;

  const markRead = async (id: string) => {
    const token = await getApiToken();
    await notificationsApi.markRead(token, id, orgId);
    await qc.invalidateQueries({ queryKey: ["merchant-notification-inbox", orgId] });
  };

  const markAll = async () => {
    const token = await getApiToken();
    await notificationsApi.markAllRead(token, orgId);
    await qc.invalidateQueries({ queryKey: ["merchant-notification-inbox", orgId] });
  };

  if (isLoaded && !isSignedIn) return null;
  if (!data && !isSignedIn) return null;

  return (
    <HeaderDropdown
      align="right"
      width="lg"
      trigger={({ open, triggerProps }) => (
        <button
          type="button"
          {...triggerProps}
          className={cn(
            "relative flex h-9 w-9 items-center justify-center rounded-full border border-primary/10 bg-white text-primary shadow-sm transition hover:bg-gray-bg",
            open && "bg-gray-bg ring-2 ring-secondary/20"
          )}
          aria-label={unread > 0 ? `${unread} unread notifications` : "Notifications"}
          title="Notifications"
        >
          <Bell className="h-4 w-4" />
          {unread > 0 ? (
            <span className="absolute -right-0.5 -top-0.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white ring-2 ring-white">
              {unread > 99 ? "99+" : unread}
            </span>
          ) : null}
        </button>
      )}
    >
      <div className="border-b border-primary/8 px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-semibold text-primary">Notifications</p>
          {unread > 0 ? (
            <button
              type="button"
              onClick={() => void markAll()}
              className="text-xs font-medium text-secondary hover:underline"
            >
              Mark all read
            </button>
          ) : null}
        </div>
      </div>
      <div className="max-h-[min(52dvh,360px)] overflow-y-auto">
        {loading ? (
          <div className="space-y-2 px-4 py-4" aria-hidden>
            <div className="h-10 animate-pulse rounded-lg bg-primary/5 motion-reduce:animate-none" />
            <div className="h-10 animate-pulse rounded-lg bg-primary/5 motion-reduce:animate-none" />
            <div className="h-10 animate-pulse rounded-lg bg-primary/5 motion-reduce:animate-none" />
          </div>
        ) : items.length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-muted">No notifications yet</p>
        ) : (
          <ul>
            {items.map((n) => (
              <li key={n.id}>
                <button
                  type="button"
                  onClick={() => {
                    if (!n.is_read) void markRead(n.id);
                    if (n.deep_link) window.location.href = n.deep_link;
                  }}
                  className={cn(
                    "flex w-full flex-col gap-0.5 border-b border-primary/5 px-4 py-3 text-left hover:bg-gray-bg",
                    !n.is_read && "bg-secondary/[0.04]"
                  )}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span
                      className={cn(
                        "truncate text-sm text-primary",
                        !n.is_read ? "font-semibold" : "font-medium"
                      )}
                    >
                      {n.title || "Update"}
                    </span>
                    <span className="shrink-0 text-[10px] text-muted">
                      {relativeTime(n.created_at)}
                    </span>
                  </span>
                  <span className="line-clamp-2 text-xs text-muted">{n.body}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="border-t border-primary/8 px-4 py-2.5">
        <Link href={viewAllHref} className="text-xs font-semibold text-secondary hover:underline">
          View all
        </Link>
      </div>
    </HeaderDropdown>
  );
}
