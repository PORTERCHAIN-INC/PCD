"use client";

import Link from "next/link";
import type { OrderDetail } from "@/lib/orders";
import { relativeTime } from "@/lib/crmFormat";
import { SectionBlock } from "@/components/orders/sections";

export function CommunicationsTab({ items }: { items: Array<Record<string, unknown>> }) {
  if (!items.length) {
    return (
      <p className="text-sm text-muted">
        No email / SMS / push notifications logged for this order
      </p>
    );
  }
  return (
    <div className="space-y-2">
      {items.map((e, i) => (
        <div
          key={String(e.id ?? i)}
          className="rounded-lg border border-primary/10 px-3 py-2 text-sm"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="font-medium">{String(e.label || e.event_type)}</p>
            <span className="rounded-full bg-gray-bg px-2 py-0.5 text-[10px] font-bold uppercase text-muted">
              {String(e.channel || "—")} · {String(e.status || "—")}
            </span>
          </div>
          <p className="mt-0.5 text-xs text-muted">
            {e.occurred_at ? relativeTime(String(e.occurred_at)) : ""}
            {e.recipient ? ` · ${String(e.recipient)}` : ""}
            {e.recipient_type ? ` · ${String(e.recipient_type)}` : ""}
          </p>
          {e.body ? <p className="mt-1 text-xs text-primary/80">{String(e.body)}</p> : null}
          {e.error ? <p className="mt-1 text-xs text-red-600">{String(e.error)}</p> : null}
        </div>
      ))}
    </div>
  );
}

export function ClaimsTab({ claims }: { claims: Array<Record<string, unknown>> }) {
  return (
    <ul className="space-y-2">
      {claims.map((c) => (
        <li key={String(c.id)} className="rounded-lg border border-primary/10 px-3 py-2 text-sm">
          <Link href={`/claims/${c.id}`} className="font-medium text-secondary hover:underline">
            {String(c.claim_type)} — {String(c.status)}
          </Link>
          {c.description ? (
            <p className="mt-1 text-xs text-muted">{String(c.description)}</p>
          ) : null}
        </li>
      ))}
      {!claims.length && <p className="text-sm text-muted">No claims on this order</p>}
    </ul>
  );
}

export function SupportTab({ tickets }: { tickets: Array<Record<string, unknown>> }) {
  return (
    <ul className="space-y-2">
      {tickets.map((t) => (
        <li key={String(t.id)} className="rounded-lg border border-primary/10 px-3 py-2 text-sm">
          <Link href={`/support/${t.id}`} className="font-medium text-secondary hover:underline">
            {String(t.subject || t.id)}
          </Link>
          <span className="ml-2 text-xs text-muted">{String(t.status || "")}</span>
        </li>
      ))}
      {!tickets.length && <p className="text-sm text-muted">No support tickets</p>}
    </ul>
  );
}

export function CareSection({ detail }: { detail: OrderDetail }) {
  return (
    <div className="space-y-8">
      <SectionBlock title="Claims">
        <ClaimsTab claims={detail.claims} />
      </SectionBlock>
      <SectionBlock title="Support">
        <SupportTab tickets={detail.support_tickets} />
      </SectionBlock>
      <SectionBlock title="Communications">
        <CommunicationsTab items={detail.communications ?? []} />
      </SectionBlock>
    </div>
  );
}
