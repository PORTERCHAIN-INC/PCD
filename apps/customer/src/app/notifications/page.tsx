"use client";

import { useAuth } from "@clerk/nextjs";
import { useCallback, useEffect, useState } from "react";
import { Bell } from "lucide-react";
import CustomerShell from "@/components/CustomerShell";
import { notificationsApi, type InboxNotification } from "@/lib/notifications";
import { cn } from "@/lib/utils";

export default function CustomerNotificationsPage() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [items, setItems] = useState<InboxNotification[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!isSignedIn) return;
    setLoading(true);
    try {
      const token = await getToken();
      if (!token) throw new Error("Not authenticated");
      const data = await notificationsApi.inbox(token, 100);
      setItems(data.items);
      setUnread(data.unread_count);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [getToken, isSignedIn]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    void refresh();
  }, [isLoaded, isSignedIn, refresh]);

  return (
    <CustomerShell>
      <div className="space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold text-primary">
              <Bell className="h-6 w-6 text-secondary" />
              Notifications
            </h1>
            <p className="text-sm text-muted">{unread} unread</p>
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
              className="rounded-xl border border-primary/10 bg-white px-3 py-2 text-sm font-medium text-primary hover:bg-gray-bg"
            >
              Mark all read
            </button>
          ) : null}
        </div>

        {!isLoaded ? (
          <p className="text-muted">Loading…</p>
        ) : !isSignedIn ? (
          <p className="text-muted">Please sign in to view notifications.</p>
        ) : error ? (
          <p className="text-sm text-red-600">{error}</p>
        ) : loading && items.length === 0 ? (
          <p className="text-muted">Loading…</p>
        ) : items.length === 0 ? (
          <p className="rounded-2xl border border-primary/10 bg-white px-6 py-12 text-center text-sm text-muted">
            No notifications yet.
          </p>
        ) : (
          <ul className="divide-y divide-primary/5 overflow-hidden rounded-2xl border border-primary/10 bg-white">
            {items.map((n) => (
              <li key={n.id}>
                <button
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
                    "flex w-full flex-col gap-1 px-5 py-4 text-left transition hover:bg-gray-bg/80",
                    !n.is_read && "bg-secondary/5"
                  )}
                >
                  <span className="font-medium text-primary">{n.title}</span>
                  <span className="text-sm text-muted">{n.body}</span>
                  <span className="text-xs text-muted">
                    {new Date(n.created_at).toLocaleString()}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </CustomerShell>
  );
}
