"use client";

import { useState } from "react";
import Link from "next/link";
import { useApiData } from "@/hooks/useApiData";
import { drivers } from "@/lib/drivers";
import { ListPager } from "@/components/crm/ListPager";
import { Badge, SectionCard } from "@/components/crm/primitives";
import { money, shortDate, titleCase } from "@/lib/crmFormat";

export function OrdersTab({ id, blockers }: { id: string; blockers: string[] }) {
  const [offset, setOffset] = useState(0);
  const { data } = useApiData((t) => drivers.orders(t, id, { limit: 50, offset }), [id, offset], {
    key: `driver-orders-${id}-${offset}`,
  });
  const items = data?.items ?? [];
  return (
    <SectionCard title={`Orders (${data?.total ?? 0})`}>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-primary/10 bg-gray-bg/40 text-xs uppercase text-muted">
            <tr>
              <th className="px-4 py-2">Order</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Amount</th>
              <th className="px-4 py-2">Scheduled</th>
              <th className="px-4 py-2">Created</th>
            </tr>
          </thead>
          <tbody>
            {items.map((o) => (
              <tr key={o.id} className="border-b border-primary/5">
                <td className="px-4 py-2 font-medium text-primary">
                  <Link href={`/orders/${o.id}`} className="text-secondary hover:underline">
                    {o.order_number}
                  </Link>
                </td>
                <td className="px-4 py-2">
                  <Badge tone="sky">{titleCase(o.state)}</Badge>
                </td>
                <td className="px-4 py-2">{money(o.amount_cents)}</td>
                <td className="px-4 py-2">{shortDate(o.scheduled_at)}</td>
                <td className="px-4 py-2">{shortDate(o.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && (
          <p className="px-5 py-10 text-center text-sm text-muted">
            No orders are assigned to this driver. Assign from the order.
            {blockers.length > 0 ? ` ${blockers.join(" ")}` : ""}
          </p>
        )}
      </div>
      <div className="px-4 pb-3">
        <ListPager
          total={data?.total ?? 0}
          limit={data?.limit ?? 50}
          offset={offset}
          onPage={setOffset}
        />
      </div>
    </SectionCard>
  );
}
