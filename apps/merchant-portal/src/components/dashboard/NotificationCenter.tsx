"use client";

import type { DashboardNotification } from "@/lib/api";
import { notificationsApi } from "@/lib/notifications";
import { formatDate } from "@/lib/utils";
import { Bell } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

interface NotificationCenterProps {
  items: DashboardNotification[];
  getToken: () => Promise<string>;
  orgId?: string;
  onRead?: () => void;
}

export function NotificationCenter({ items, getToken, orgId, onRead }: NotificationCenterProps) {
  const router = useRouter();
  const [localItems, setLocalItems] = useState(items);

  const displayItems = localItems.length ? localItems : items;
  const unread = displayItems.filter((n) => !n.is_read).length;

  const handleClick = async (item: DashboardNotification) => {
    if (!item.is_read) {
      try {
        const token = await getToken();
        await notificationsApi.markRead(token, item.id, orgId);
        setLocalItems((prev) => prev.map((n) => (n.id === item.id ? { ...n, is_read: true } : n)));
        onRead?.();
      } catch {
        /* ignore mark-read errors */
      }
    }
    if (item.deep_link) {
      if (item.deep_link.startsWith("http")) {
        window.open(item.deep_link, "_blank", "noopener,noreferrer");
      } else {
        router.push(item.deep_link);
      }
    }
  };

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Bell className="h-5 w-5 text-secondary" />
          <h2 className="text-lg font-semibold text-primary">Notification Center</h2>
        </div>
        {unread > 0 && (
          <span className="rounded-full bg-secondary px-2 py-0.5 text-xs font-semibold text-white">
            {unread} new
          </span>
        )}
      </div>
      <ul className="mt-4 max-h-72 space-y-3 overflow-y-auto">
        {displayItems.length === 0 ? (
          <li className="text-sm text-muted">No notifications yet.</li>
        ) : (
          displayItems.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => void handleClick(item)}
                className={`w-full rounded-xl border px-3 py-2 text-left text-sm transition hover:border-secondary/40 ${
                  item.is_read
                    ? "border-primary/5 bg-slate-50/50"
                    : "border-secondary/20 bg-secondary/5"
                }`}
              >
                <p className="font-medium text-primary">{item.title}</p>
                <p className="mt-0.5 text-muted">{item.body}</p>
                <p className="mt-1 text-xs text-muted">{formatDate(item.created_at)}</p>
                {item.deep_link && <p className="mt-1 text-xs text-secondary">View details →</p>}
              </button>
            </li>
          ))
        )}
      </ul>
      <p className="mt-3 text-xs text-muted">
        Preferences in{" "}
        <Link href="/settings" className="text-secondary underline">
          Settings → Notifications
        </Link>
      </p>
    </section>
  );
}
