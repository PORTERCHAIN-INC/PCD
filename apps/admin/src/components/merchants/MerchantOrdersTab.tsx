"use client";

import { useState } from "react";
import Link from "next/link";
import { cn } from "@porterchain/ui/utils";
import { useApiData } from "@/hooks/useApiData";
import { merchants } from "@/lib/merchants";
import MerchantStandingOrdersCard from "@/components/merchants/MerchantStandingOrdersCard";
import { ListPager } from "@/components/crm/ListPager";
import { Badge, Input, SectionCard } from "@/components/crm/primitives";
import { money, shortDate, titleCase } from "@/lib/crmFormat";

const ORDER_FILTER_STATES = [
  "DISPATCH_READY",
  "DRIVER_ASSIGNED",
  "IN_TRANSIT",
  "DELIVERED",
  "POD_COMPLETED",
  "CANCELLED",
  "FAILED",
] as const;

export function OrdersTab({ id }: { id: string }) {
  const [offset, setOffset] = useState(0);
  const [state, setState] = useState<string>("");
  const [q, setQ] = useState("");
  const { data } = useApiData(
    (t) =>
      merchants.orders(t, id, {
        limit: 50,
        offset,
        state: state || undefined,
      }),
    [id, offset, state],
    {
      key: `merchant-orders-${id}-${offset}-${state || "all"}`,
    }
  );
  const items = data?.items ?? [];
  const needle = q.trim().toLowerCase();
  const visible = needle
    ? items.filter((o) => {
        const hay =
          `${o.order_number ?? ""} ${o.tracking_number ?? ""} ${o.state ?? ""}`.toLowerCase();
        return hay.includes(needle);
      })
    : items;
  const grouped = new Map<string, typeof visible>();
  const loose: typeof visible = [];
  for (const order of visible) {
    const jobId = order.route_import_job_id;
    if (jobId) {
      const rows = grouped.get(jobId) ?? [];
      rows.push(order);
      grouped.set(jobId, rows);
    } else {
      loose.push(order);
    }
  }
  return (
    <div className="space-y-5">
      <MerchantStandingOrdersCard id={id} />
      <SectionCard title={`Orders (${data?.total ?? 0})`}>
        <div className="space-y-3 border-b border-primary/5 px-4 py-3 sm:px-5">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => {
                setState("");
                setOffset(0);
              }}
              className={cn(
                "rounded-lg px-2.5 py-1 text-xs font-medium",
                !state ? "bg-secondary text-white" : "bg-gray-bg text-muted hover:text-primary"
              )}
            >
              All
            </button>
            {ORDER_FILTER_STATES.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => {
                  setState(s);
                  setOffset(0);
                }}
                className={cn(
                  "rounded-lg px-2.5 py-1 text-xs font-medium",
                  state === s
                    ? "bg-secondary text-white"
                    : "bg-gray-bg text-muted hover:text-primary"
                )}
              >
                {titleCase(s)}
              </button>
            ))}
          </div>
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Filter this page by order / tracking…"
            className="max-w-sm"
          />
        </div>
        <div className="ops-table-scroll">
          <table className="w-full min-w-[36rem] text-left text-sm">
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
              {[...grouped.entries()].map(([jobId, rows]) => (
                <OrdersGroupRows key={jobId} label={`Route job ${jobId.slice(0, 8)}`} rows={rows} />
              ))}
              {loose.length > 0 && grouped.size > 0 ? (
                <OrdersGroupRows label="Other orders" rows={loose} />
              ) : null}
              {grouped.size === 0 ? visible.map((o) => <OrderRow key={o.id} order={o} />) : null}
            </tbody>
          </table>
          {visible.length === 0 && (
            <p className="px-5 py-10 text-center text-sm text-muted">No orders match.</p>
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
    </div>
  );
}

function OrdersGroupRows({
  label,
  rows,
}: {
  label: string;
  rows: Array<{
    id: string;
    order_number: string;
    state: string;
    amount_cents: number;
    scheduled_at: string | null;
    created_at: string | null;
  }>;
}) {
  return (
    <>
      <tr className="bg-gray-bg/60">
        <td
          colSpan={5}
          className="px-4 py-2 text-xs font-semibold uppercase tracking-wide text-muted"
        >
          {label}
        </td>
      </tr>
      {rows.map((order) => (
        <OrderRow key={order.id} order={order} />
      ))}
    </>
  );
}

function OrderRow({
  order,
}: {
  order: {
    id: string;
    order_number: string;
    state: string;
    amount_cents: number;
    scheduled_at: string | null;
    created_at: string | null;
  };
}) {
  return (
    <tr className="border-b border-primary/5">
      <td className="px-4 py-2 font-medium text-primary">
        <Link href={`/orders/${order.id}`} className="text-secondary hover:underline">
          {order.order_number}
        </Link>
      </td>
      <td className="px-4 py-2">
        <Badge tone="sky">{titleCase(order.state)}</Badge>
      </td>
      <td className="px-4 py-2">{money(order.amount_cents)}</td>
      <td className="px-4 py-2">{shortDate(order.scheduled_at)}</td>
      <td className="px-4 py-2">{shortDate(order.created_at)}</td>
    </tr>
  );
}
