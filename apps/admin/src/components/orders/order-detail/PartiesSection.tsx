"use client";

import Link from "next/link";
import { User, Truck } from "lucide-react";
import { formatCents } from "@porterchain/ui/utils";
import { formatState, type OrderDetail } from "@/lib/orders";
import { Button } from "@/components/crm/primitives";
import { SectionBlock } from "@/components/orders/sections";
import { EntityRows, Row } from "./shared";

export function Merchant360Tab({ detail }: { detail: OrderDetail }) {
  const m = detail.merchant;
  if (!m) return <p className="text-sm text-muted">No merchant linked</p>;
  return (
    <div className="space-y-4">
      <EntityRows data={m} />
      <div className="flex gap-2">
        {m.id ? (
          <Link href={`/merchants/${String(m.id)}`}>
            <Button variant="outline" className="px-2 py-1 text-xs">
              <User className="h-4 w-4" /> Merchant profile
            </Button>
          </Link>
        ) : null}
      </div>
    </div>
  );
}

export function Customer360Tab({ detail }: { detail: OrderDetail }) {
  const c360 = detail.customer_360;
  const customerId = (c360?.id as string | undefined) || detail.customer_id || null;
  return (
    <div className="space-y-4">
      <Row label="Email" value={detail.customer_email || "—"} />
      <Row label="Phone" value={detail.customer_phone || "—"} />
      {c360 ? (
        <>
          <Row label="Lifetime orders" value={String(c360.lifetime_orders ?? "—")} />
          <Row
            label="Lifetime revenue"
            value={
              c360.lifetime_revenue_cents != null
                ? formatCents(Number(c360.lifetime_revenue_cents))
                : "—"
            }
          />
          {(c360.recent_orders as Array<Record<string, unknown>> | undefined)?.length ? (
            <div>
              <p className="mb-2 text-sm font-semibold">Recent orders</p>
              <ul className="space-y-1">
                {(c360.recent_orders as Array<Record<string, unknown>>).map((o) => (
                  <li key={String(o.order_id)}>
                    <Link
                      href={`/orders/${o.order_id}`}
                      className="text-sm text-secondary hover:underline"
                    >
                      {String(o.order_number)} — {formatState(String(o.state))}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      ) : null}
      {customerId ? (
        <Link href={`/customers/${customerId}`}>
          <Button variant="outline" className="px-2 py-1 text-xs">
            <User className="h-4 w-4" /> Customer profile
          </Button>
        </Link>
      ) : null}
    </div>
  );
}

export function Driver360Tab({ detail }: { detail: OrderDetail }) {
  const d = detail.driver;
  if (!d) return <p className="text-sm text-muted">No driver assigned</p>;
  return (
    <div className="space-y-4">
      <EntityRows data={d} />
      {d.id ? (
        <Link href={`/drivers/${String(d.id)}`}>
          <Button variant="outline" className="px-2 py-1 text-xs">
            <Truck className="h-4 w-4" /> Driver profile
          </Button>
        </Link>
      ) : null}
    </div>
  );
}

export function Vehicle360Tab({ detail }: { detail: OrderDetail }) {
  const v = detail.vehicle;
  if (!v) return <p className="text-sm text-muted">No vehicle assigned</p>;
  return <EntityRows data={v} />;
}

export function PartiesSection({ detail }: { detail: OrderDetail }) {
  return (
    <div className="space-y-8">
      <SectionBlock title="Merchant">
        <Merchant360Tab detail={detail} />
      </SectionBlock>
      <SectionBlock title="Customer">
        <Customer360Tab detail={detail} />
      </SectionBlock>
      <SectionBlock title="Driver">
        <Driver360Tab detail={detail} />
      </SectionBlock>
      <SectionBlock title="Vehicle">
        <Vehicle360Tab detail={detail} />
      </SectionBlock>
    </div>
  );
}
