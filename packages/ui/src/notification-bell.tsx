"use client";

import Link from "next/link";
import { Bell, CheckCheck, Inbox, Sparkles } from "lucide-react";
import { HeaderDropdown } from "./header-dropdown";
import { cn } from "./utils";

export type NotificationBellItem = {
  id: string;
  title?: string | null;
  body?: string | null;
  priority?: string | null;
  deep_link?: string | null;
  is_read: boolean;
  created_at?: string | null;
};

export type NotificationBellProps = {
  items: NotificationBellItem[];
  unread: number;
  loading: boolean;
  onMarkRead: (id: string) => void | Promise<unknown>;
  onMarkAll: () => void | Promise<unknown>;
  viewAllHref: string;
  /** "ops" is the admin Notification Center look (priority dots, larger panel). */
  variant?: "standard" | "ops";
  /** Show "N unread" under the title (standard variant). */
  showUnreadCount?: boolean;
  emptyHint?: string;
  /** Called when the bell is clicked, before the panel toggles. */
  onTriggerClick?: () => void;
};

export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return "";
  const mins = Math.round((Date.now() - t) / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.round(mins / 60);
  if (hrs < 48) return `${hrs}h`;
  return `${Math.round(hrs / 24)}d`;
}

function PriorityDot({ priority }: { priority?: string | null }) {
  const tone =
    priority === "critical" || priority === "high"
      ? "bg-red-500"
      : priority === "medium"
        ? "bg-amber-500"
        : "bg-secondary";
  return <span className={cn("mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full", tone)} aria-hidden />;
}

/** Header bell + inbox dropdown shared by every web portal; data comes from the portal. */
export function NotificationBell({
  items,
  unread,
  loading,
  onMarkRead,
  onMarkAll,
  viewAllHref,
  variant = "standard",
  showUnreadCount = true,
  emptyHint,
  onTriggerClick,
}: NotificationBellProps) {
  const ops = variant === "ops";
  const title = ops ? "Notification Center" : "Notifications";
  return (
    <HeaderDropdown
      align="right"
      width={ops ? "2xl" : "lg"}
      className={ops ? "overflow-hidden shadow-2xl shadow-primary/20" : undefined}
      trigger={({ open, triggerProps }) => (
        <button
          type="button"
          {...triggerProps}
          onClick={() => {
            onTriggerClick?.();
            triggerProps.onClick();
          }}
          className={cn(
            "relative flex items-center justify-center rounded-full border border-primary/10 bg-white text-primary shadow-sm transition",
            ops
              ? "group h-10 w-10 hover:border-secondary/25 hover:bg-gradient-to-br hover:from-secondary/5 hover:to-white"
              : "h-9 w-9 hover:bg-gray-bg",
            open &&
              (ops
                ? "border-secondary/30 bg-gradient-to-br from-secondary/10 to-white ring-2 ring-secondary/20"
                : "bg-gray-bg ring-2 ring-secondary/20")
          )}
          aria-label={unread > 0 ? `${unread} unread notifications` : title}
          title={title}
        >
          {ops ? (
            <span
              className={cn(
                "pointer-events-none absolute inset-0 rounded-full opacity-0 transition duration-500",
                "bg-[radial-gradient(circle_at_30%_20%,rgba(14,165,233,0.18),transparent_55%)]",
                (open || unread > 0) && "opacity-100"
              )}
              aria-hidden
            />
          ) : null}
          <Bell
            className={cn(
              ops ? "relative h-[18px] w-[18px] transition-transform duration-300" : "h-4 w-4",
              ops && open && "scale-110 text-secondary",
              ops && unread > 0 && "text-secondary"
            )}
          />
          {unread > 0 ? (
            <span className="absolute -right-0.5 -top-0.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-gradient-to-br from-red-500 to-rose-600 px-1 text-[10px] font-bold text-white shadow-sm ring-2 ring-white">
              {unread > 99 ? "99+" : unread}
            </span>
          ) : null}
        </button>
      )}
    >
      <div
        className={cn(
          "relative border-b border-primary/8",
          ops
            ? "overflow-hidden bg-gradient-to-br from-slate-50 via-white to-sky-50/40 px-4 py-4"
            : "px-4 py-3"
        )}
      >
        {ops ? (
          <div
            className="pointer-events-none absolute -right-8 -top-10 h-28 w-28 rounded-full bg-secondary/10 blur-2xl"
            aria-hidden
          />
        ) : null}
        <div className="relative flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            {ops ? (
              <span className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-xl bg-secondary/10 text-secondary ring-1 ring-secondary/15">
                <Sparkles className="h-4 w-4" />
              </span>
            ) : null}
            <div>
              <p className="text-sm font-semibold text-primary">{title}</p>
              {ops ? (
                <p className="text-xs text-muted">
                  {unread > 0
                    ? `${unread} unread update${unread === 1 ? "" : "s"}`
                    : "You’re all caught up"}
                </p>
              ) : showUnreadCount ? (
                <p className="text-xs text-muted">{unread} unread</p>
              ) : null}
            </div>
          </div>
          {unread > 0 ? (
            <button
              type="button"
              onClick={() => void onMarkAll()}
              className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-secondary transition hover:bg-secondary/10"
            >
              {ops ? <CheckCheck className="h-3.5 w-3.5" /> : null}
              {ops ? "Mark all" : "Mark all read"}
            </button>
          ) : null}
        </div>
      </div>

      <div className="max-h-[min(52dvh,380px)] overflow-y-auto">
        {loading ? (
          <div className="space-y-3 px-4 py-5" aria-hidden>
            {[0, 1, 2].map((i) => (
              <div key={i} className="animate-pulse space-y-2 motion-reduce:animate-none">
                <div className="h-3 w-[66%] rounded bg-primary/10" />
                <div className="h-2.5 w-full rounded bg-primary/5" />
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-6 py-10 text-center">
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/5 text-muted">
              <Inbox className="h-5 w-5" />
            </span>
            <p className="text-sm font-medium text-primary">No notifications yet</p>
            {emptyHint ? <p className="max-w-[220px] text-xs text-muted">{emptyHint}</p> : null}
          </div>
        ) : (
          <ul>
            {items.map((n) => (
              <li key={n.id}>
                <button
                  type="button"
                  onClick={() => {
                    if (!n.is_read) void onMarkRead(n.id);
                    if (n.deep_link) window.location.href = n.deep_link;
                  }}
                  className={cn(
                    "flex w-full gap-3 border-b border-primary/5 px-4 py-3 text-left transition",
                    "hover:bg-gradient-to-r hover:from-secondary/[0.06] hover:to-transparent",
                    !n.is_read && "bg-secondary/[0.04]"
                  )}
                >
                  {ops ? <PriorityDot priority={n.priority} /> : null}
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
                    {ops && !n.is_read ? (
                      <span className="mt-1.5 inline-flex rounded-full bg-secondary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-secondary">
                        New
                      </span>
                    ) : null}
                  </span>
                </button>
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
          {ops ? "Open Notification Center" : "View all"}
        </Link>
      </div>
    </HeaderDropdown>
  );
}

export default NotificationBell;
