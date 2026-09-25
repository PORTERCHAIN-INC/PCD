"use client";

import { use } from "react";
import dynamic from "next/dynamic";
import { Spinner } from "@/components/crm/primitives";

const OrderDetailPageClient = dynamic(() => import("@/components/orders/OrderDetailPageClient"), {
  loading: () => <Spinner label="Loading order…" />,
  ssr: false,
});

export default function OrderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <OrderDetailPageClient id={id} />;
}
