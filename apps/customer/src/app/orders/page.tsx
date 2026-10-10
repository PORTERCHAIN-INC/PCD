import { Suspense } from "react";
import OrdersClient from "@/components/orders/OrdersClient";

export default function OrdersPage() {
  return (
    <Suspense fallback={null}>
      <OrdersClient />
    </Suspense>
  );
}
