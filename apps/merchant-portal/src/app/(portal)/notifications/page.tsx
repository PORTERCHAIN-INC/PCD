"use client";

import dynamic from "next/dynamic";
import { PageSkeleton } from "@porterchain/ui/loading";

const NotificationsPageClient = dynamic(
  () => import("@/components/notifications/NotificationsPageClient"),
  { loading: () => <PageSkeleton rows={3} /> }
);

export default function MerchantNotificationsPage() {
  return <NotificationsPageClient />;
}
