"use client";

import dynamic from "next/dynamic";
import { PageSkeleton } from "@porterchain/ui/loading";

const OrdersListClient = dynamic(() => import("@/components/orders/OrdersListClient"), {
  loading: () => <PageSkeleton rows={4} />,
});

export default function OrdersPage() {
  return <OrdersListClient />;
}
