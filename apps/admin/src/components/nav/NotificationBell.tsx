"use client";

import Link from "next/link";
import { useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Bell, CheckCheck, Inbox, Sparkles } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import HeaderDropdown from "@/components/nav/HeaderDropdown";
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

function PriorityDot({ priority }: { priority: string }) {
  const tone =
    priority === "critical" || priority === "high"
      ? "bg-red-500"
      : priority === "medium"
        ? "bg-amber-500"
        : "bg-secondary";
  return <span className={cn("mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full", tone)} aria-hidden />;
}

export default function NotificationBell({
  viewAllHref = "/notifications",
}: {
  viewAllHref?: string;
}) {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const qc = useQueryClient();
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");

  const { data, isLoading } = useQuery({
    queryKey: ["admin-notification-inbox"],
    enabled,
    refetchInterval: 45_000,
    queryFn: async () => loadInbox(await getApiToken()),
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
    <HeaderDropdown
      align="right"
      width="2xl"
      className="overflow-hidden shadow-2xl shadow-primary/20"
      trigger={({ open, triggerProps }) => (
        <button
          type="button"
          {...triggerProps}
          className={cn(
            "group relative flex h-10 w-10 items-center justify-center rounded-full border border-primary/10 bg-white text-primary shadow-sm transition",
            "hover:border-secondary/25 hover:bg-gradient-to-br hover:from-secondary/5 hover:to-white",
            open &&
              "border-secondary/30 bg-gradient-to-br from-secondary/10 to-white ring-2 ring-secondary/20"
          )}
          aria-label={unread > 0 ? `${unread} unread notifications` : "Notification Center"}
          title="Notification Center"
        >
          <span
            className={cn(
              "pointer-events-none absolute inset-0 rounded-full opacity-0 transition duration-500",
              "bg-[radial-gradient(circle_at_30%_20%,rgba(14,165,233,0.18),transparent_55%)]",
              (open || unread > 0) && "opacity-100"
            )}
            aria-hidden
          />
          <Bell
            className={cn(
              "relative h-[18px] w-[18px] transition-transform duration-300",
              open && "scale-110 text-secondary",
              unread > 0 && "text-secondary"
            )}
          />
          <AnimatePresence>
            {unread > 0 ? (
              <motion.span
                key="badge"
                initial={{ scale: 0.5, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.5, opacity: 0 }}
                className="absolute -right-0.5 -top-0.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-gradient-to-br from-red-500 to-rose-600 px-1 text-[10px] font-bold text-white shadow-sm ring-2 ring-white"
              >
                {unread > 99 ? "99+" : unread}
              </motion.span>
            ) : null}
          </AnimatePresence>
        </button>
      )}
    >
      <div className="relative overflow-hidden border-b border-primary/8 bg-gradient-to-br from-slate-50 via-white to-sky-50/40 px-4 py-4">
        <div
          className="pointer-events-none absolute -right-8 -top-10 h-28 w-28 rounded-full bg-secondary/10 blur-2xl"
          aria-hidden
        />
        <div className="relative flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-xl bg-secondary/10 text-secondary ring-1 ring-secondary/15">
              <Sparkles className="h-4 w-4" />
            </span>
            <div>
              <p className="text-sm font-semibold text-primary">Notification Center</p>
              <p className="text-xs text-muted">
                {unread > 0
                  ? `${unread} unread update${unread === 1 ? "" : "s"}`
                  : "You’re all caught up"}
              </p>
            </div>
          </div>
          {unread > 0 ? (
            <button
              type="button"
              onClick={() => void markAll()}
              className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-secondary transition hover:bg-secondary/10"
            >
              <CheckCheck className="h-3.5 w-3.5" />
              Mark all
            </button>
          ) : null}
        </div>
      </div>

      <div className="max-h-[min(52dvh,380px)] overflow-y-auto">
        {isLoading ? (
          <div className="space-y-3 px-4 py-5">
            {[0, 1, 2].map((i) => (
              <div key={i} className="animate-pulse space-y-2">
                <div className="h-3 w-[66%] rounded bg-primary/10" />
                <div className="h-2.5 w-full rounded bg-primary/5" />
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/5 text-muted">
              <Inbox className="h-5 w-5" />
            </span>
            <p className="text-sm font-medium text-primary">No notifications yet</p>
            <p className="max-w-[220px] text-xs text-muted">
              Live alerts for tickets, claims, and ops will show up here.
            </p>
          </div>
        ) : (
          <ul>
            {items.map((n, index) => (
              <li key={n.id}>
                <motion.button
                  type="button"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(index * 0.03, 0.2) }}
                  onClick={() => {
                    if (!n.is_read) void markRead(n.id);
                    if (n.deep_link) window.location.href = n.deep_link;
                  }}
                  className={cn(
                    "flex w-full gap-3 border-b border-primary/5 px-4 py-3.5 text-left transition",
                    "hover:bg-gradient-to-r hover:from-secondary/[0.06] hover:to-transparent",
                    !n.is_read && "bg-secondary/[0.04]"
                  )}
                >
                  <PriorityDot priority={n.priority} />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center justify-between gap-2">
                      <span
                        className={cn(
                          "truncate text-sm text-primary",
                          !n.is_read ? "font-semibold" : "font-medium"
                        )}
                      >
                        {n.title || "Update"}
                      </span>
                      <span className="shrink-0 text-[10px] tabular-nums text-muted">
                        {relativeTime(n.created_at)}
                      </span>
                    </span>
                    <span className="mt-0.5 line-clamp-2 text-xs leading-relaxed text-muted">
                      {n.body}
                    </span>
                    {!n.is_read ? (
                      <span className="mt-1.5 inline-flex rounded-full bg-secondary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-secondary">
                        New
                      </span>
                    ) : null}
                  </span>
                </motion.button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="border-t border-primary/8 bg-slate-50/80 px-4 py-2.5">
        <Link
          href={viewAllHref}
          className="text-xs font-semibold text-secondary transition hover:underline"
        >
          Open Notification Center
        </Link>
      </div>
    </HeaderDropdown>
  );
}
