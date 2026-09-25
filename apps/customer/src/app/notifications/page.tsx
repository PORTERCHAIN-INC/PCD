"use client";

import dynamic from "next/dynamic";

const NotificationsClient = dynamic(
  () => import("@/components/notifications/NotificationsClient"),
  { loading: () => <p className="p-8 text-sm text-muted">Loading…</p> }
);

export default function CustomerNotificationsPage() {
  return <NotificationsClient />;
}
