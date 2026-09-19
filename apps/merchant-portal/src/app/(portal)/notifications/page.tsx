"use client";

import { useCallback, useEffect, useState } from "react";
import { Bell } from "lucide-react";
import Link from "next/link";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { hasMerchantModule } from "@/lib/merchant-nav";
import { notificationsApi, type InboxNotification } from "@/lib/notifications";
import { formatDate } from "@/lib/utils";
import { cn } from "@/lib/utils";

export default function MerchantNotificationsPage() {
  const { getApiToken, orgId, isLoaded, isSignedIn, modules } = useMerchantAuth();
  const [items, setItems] = useState<InboxNotification[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!isSignedIn || !orgId) return;
    setLoading(true);
    try {
      const token = await getApiToken();
      const data = await notificationsApi.inbox(token, orgId, 100);
      setItems(data.items);
      setUnread(data.unread_count);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load notifications");
    } finally {
      setLoading(false);
    }
  }, [getApiToken, isSignedIn, orgId]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn || !orgId) return;
    void refresh();
  }, [isLoaded, isSignedIn, orgId, refresh]);

  if (!isLoaded) return <p className="text-muted">Loading…</p>;
  if (!isSignedIn) return <p className="text-muted">Please sign in.</p>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-primary">
            <Bell className="h-6 w-6 text-secondary" />
            Inbox
          </h1>
          <p className="mt-1 text-sm text-muted">
            Delivery and account alerts
            {hasMerchantModule(modules, "settings") ? (
              <>
                {" "}
                · Preferences live in{" "}
                <Link href="/settings?tab=notifications" className="text-secondary underline">
                  Settings
                </Link>
              </>
            ) : null}
          </p>
        </div>
        {unread > 0 ? (
          <button
            type="button"
            onClick={() =>
              void (async () => {
                const token = await getApiToken();
                await notificationsApi.markAllRead(token, orgId);
                await refresh();
              })()
            }
            className="rounded-xl border border-primary/10 bg-white px-3 py-2 text-sm font-medium text-primary hover:bg-gray-bg"
          >
            Mark all read
          </button>
        ) : null}
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      {loading && items.length === 0 ? (
        <p className="text-muted">Loading…</p>
      ) : items.length === 0 ? (
        <div className="rounded-2xl border border-primary/10 bg-white px-6 py-16 text-center">
          <p className="font-medium text-primary">No notifications yet</p>
          {hasMerchantModule(modules, "settings") ? (
            <p className="mt-1 text-sm text-muted">
              Preferences and quiet hours live in{" "}
              <Link href="/settings?tab=notifications" className="text-secondary underline">
                Settings
              </Link>
              .
            </p>
          ) : (
            <p className="mt-1 text-sm text-muted">
              Ask your owner to change company alert preferences.
            </p>
          )}
        </div>
      ) : (
        <ul className="divide-y divide-primary/5 overflow-hidden rounded-2xl border border-primary/10 bg-white">
          {items.map((n) => (
            <li key={n.id}>
              <button
                type="button"
                onClick={() =>
                  void (async () => {
                    if (!n.is_read) {
                      const token = await getApiToken();
                      await notificationsApi.markRead(token, n.id, orgId);
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
                <span className="flex items-center justify-between gap-2">
                  <span className="font-medium text-primary">{n.title}</span>
                  <span className="text-xs text-muted">{formatDate(n.created_at)}</span>
                </span>
                <span className="text-sm text-muted">{n.body}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
