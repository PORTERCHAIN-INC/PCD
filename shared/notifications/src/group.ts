import type { NotificationInboxItem } from "./types";

const CUSTOMER_GROUPS: Record<string, string> = {
  orders: "Shipments",
  tracking: "Tracking",
  payments: "Payments",
  support: "Support",
  claims: "Claims",
  marketing: "Updates",
};

const DRIVER_GROUP_LABELS: Record<string, string> = {
  assignment: "Assignments",
  route_changes: "Route changes",
  emergency: "Emergency",
  support: "Support",
  claims: "Claims",
};

export function groupLabel(key: string, mode: "driver" | "customer"): string {
  if (mode === "driver") return DRIVER_GROUP_LABELS[key] ?? key;
  return CUSTOMER_GROUPS[key] ?? key.replace(/_/g, " ");
}

export function groupInboxItems(
  items: NotificationInboxItem[],
  byGroup: Record<string, NotificationInboxItem[]> | undefined,
  mode: "driver" | "customer"
): Array<{ key: string; label: string; items: NotificationInboxItem[] }> {
  if (byGroup && Object.keys(byGroup).length > 0) {
    return Object.entries(byGroup)
      .filter(([, groupItems]) => groupItems.length > 0)
      .map(([key, groupItems]) => ({
        key,
        label: groupLabel(key, mode),
        items: groupItems,
      }));
  }

  const buckets = new Map<string, NotificationInboxItem[]>();
  for (const item of items) {
    const key = item.group ?? item.category ?? "general";
    const list = buckets.get(key) ?? [];
    list.push(item);
    buckets.set(key, list);
  }

  return Array.from(buckets.entries()).map(([key, groupItems]) => ({
    key,
    label: groupLabel(key, mode),
    items: groupItems,
  }));
}

export function filterInboxItems(
  items: NotificationInboxItem[],
  filter: "all" | "unread" | "read"
) {
  if (filter === "unread") return items.filter((item) => !item.is_read);
  if (filter === "read") return items.filter((item) => item.is_read);
  return items;
}
