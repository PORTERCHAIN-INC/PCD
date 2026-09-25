"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell } from "lucide-react";
import CustomerShell from "@/components/CustomerShell";
import CustomerMotion from "@/components/motion/CustomerMotion";
import { isClerkConfigured } from "@/lib/env";
import { notificationsApi } from "@/lib/notifications";
import { cn } from "@/lib/utils";

const INBOX_KEY = ["customer-notification-inbox"] as const;

export default function NotificationsClient() {
  if (!isClerkConfigured()) {
    return (
      <CustomerShell>
        <p className="text-muted">Please sign in to view notifications.</p>
      </CustomerShell>
    );
  }
  return <CustomerNotificationsWithClerk />;
}

function CustomerNotificationsWithClerk() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const qc = useQueryClient();
  const enabled = Boolean(isLoaded && isSignedIn);

  const {
    data,
    isLoading: loading,
    error: queryError,
  } = useQuery({
    queryKey: INBOX_KEY,
    enabled,
    staleTime: 30_000,
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("Not authenticated");
      return notificationsApi.inbox(token, 100);
    },
  });

  const items = data?.items ?? [];
  const unread = data?.unread_count ?? 0;
  const error =
    queryError instanceof Error ? queryError.message : queryError ? "Failed to load" : null;

  async function refresh() {
    await qc.invalidateQueries({ queryKey: INBOX_KEY });
  }

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
          <div className="rounded-2xl border border-primary/10 bg-white px-6 py-8 text-center">
            <CustomerMotion name="inbox" size={140} />
            <p className="text-sm font-semibold text-primary">No alerts yet</p>
            <p className="mt-1 text-sm text-muted">Shipment updates appear in this list.</p>
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
