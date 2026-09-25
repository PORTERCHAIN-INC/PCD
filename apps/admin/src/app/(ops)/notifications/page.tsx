"use client";

import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const NotificationsCenterClient = dynamic(
  () => import("@/components/notifications/NotificationsCenterClient"),
  { loading: () => <Spinner label="Loading notifications…" /> }
);

export default function NotificationsPage() {
  return <NotificationsCenterClient />;
}
