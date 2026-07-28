"use client";

import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { useCallback, useEffect, useState } from "react";
import { Bell } from "lucide-react";
import { cn } from "@/lib/utils";
import HeaderDropdown from "@/components/nav/HeaderDropdown";
import { isClerkConfigured } from "@/lib/env";
import { notificationsApi, type InboxNotification } from "@/lib/notifications";

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
  if (!isClerkConfigured()) return null;
  return <NotificationBellWithClerk viewAllHref={viewAllHref} />;
}

function NotificationBellWithClerk({ viewAllHref }: { viewAllHref: string }) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [items, setItems] = useState<InboxNotification[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!isSignedIn) return;
    try {
      const token = await getToken();
      if (!token) return;
      const data = await notificationsApi.inbox(token, 20);
      setItems(data.items);
      setUnread(data.unread_count);
    } catch {
      /* keep last */
    } finally {
      setLoading(false);
    }
  }, [getToken, isSignedIn]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    void refresh();
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, 45_000);
    return () => window.clearInterval(id);
  }, [isLoaded, isSignedIn, refresh]);

  if (!isLoaded || !isSignedIn) return null;

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
            <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-bold text-white">
              {unread > 99 ? "99+" : unread}
            </span>
          ) : null}
        </button>
      )}
    >
      <div className="border-b border-primary/8 px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <div>
            <p className="text-sm font-semibold text-primary">Notifications</p>
            <p className="text-xs text-muted">{unread} unread</p>
          </div>
          {unread > 0 ? (
            <button
              type="button"
              onClick={() =>
                void (async () => {
                  const token = await getToken();
                  if (!token) return;
                  await notificationsApi.markAllRead(token);
                  await refresh();
                })()
              }
              className="text-xs font-medium text-secondary hover:underline"
            >
              Mark all read
            </button>
          ) : null}
        </div>
      </div>
      <div className="max-h-[min(50dvh,360px)] overflow-y-auto">
        {loading ? (
          <p className="px-4 py-8 text-center text-sm text-muted">Loading…</p>
        ) : items.length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-muted">No notifications yet</p>
        ) : (
          items.map((n) => (
            <button
              key={n.id}
              type="button"
              onClick={() =>
                void (async () => {
                  if (!n.is_read) {
                    const token = await getToken();
                    if (token) await notificationsApi.markRead(token, n.id);
                    await refresh();
                  }
                  if (n.deep_link) window.location.href = n.deep_link;
                })()
              }
              className={cn(
                "flex w-full flex-col gap-0.5 border-b border-primary/5 px-4 py-3 text-left transition hover:bg-gray-bg",
                !n.is_read && "bg-secondary/5"
              )}
            >
              <span className="flex items-center justify-between gap-2">
                <span className="truncate text-sm font-medium text-primary">
                  {n.title || "Update"}
                </span>
                <span className="shrink-0 text-[10px] text-muted">
                  {relativeTime(n.created_at)}
                </span>
              </span>
              <span className="line-clamp-2 text-xs text-muted">{n.body}</span>
            </button>
          ))
        )}
      </div>
      <div className="border-t border-primary/8 px-4 py-2.5">
        <Link href={viewAllHref} className="text-xs font-medium text-secondary hover:underline">
          View all
        </Link>
      </div>
    </HeaderDropdown>
  );
}
