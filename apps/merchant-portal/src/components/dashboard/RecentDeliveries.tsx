import type { DashboardDelivery } from "@/lib/api";
import { formatCents, formatDate } from "@/lib/utils";
import Link from "next/link";

interface RecentDeliveriesProps {
  items: DashboardDelivery[];
}

export function RecentDeliveries({ items }: RecentDeliveriesProps) {
  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-primary">Recent Deliveries</h2>
        <Link href="/orders" className="text-sm font-medium text-secondary hover:underline">
          View all
        </Link>
      </div>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[32rem] text-left text-sm">
          <thead>
            <tr className="border-b border-primary/10 text-muted">
              <th className="pb-2 font-medium">Order</th>
              <th className="pb-2 font-medium">Destination</th>
              <th className="pb-2 font-medium">Amount</th>
              <th className="pb-2 font-medium">Delivered</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-4 text-muted">
                  No recent deliveries.
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={item.order_id} className="border-b border-primary/5">
                  <td className="py-3">
                    <Link
                      href={`/orders/${item.order_id}`}
                      className="font-medium text-secondary hover:underline"
                    >
                      {item.tracking_number}
                    </Link>
                  </td>
                  <td className="max-w-[12rem] truncate py-3 text-muted">{item.dropoff ?? "—"}</td>
                  <td className="py-3">{formatCents(item.amount_cents)}</td>
                  <td className="py-3 text-muted">{formatDate(item.delivered_at)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
