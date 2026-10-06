"use client";

import type { OrderDetail } from "@/lib/orders";
import { relativeTime } from "@/lib/crmFormat";
import { SectionBlock } from "@/components/orders/sections";
import { Row } from "./shared";

export function EventListTab({
  items,
  empty,
}: {
  items: Array<Record<string, unknown>>;
  empty: string;
}) {
  return (
    <div className="space-y-2">
      {items.map((e, i) => (
        <div key={i} className="rounded-lg border border-primary/10 px-3 py-2 text-sm">
          <p className="font-medium">{String(e.label || e.event_type)}</p>
          <p className="text-xs text-muted">
            {e.occurred_at ? relativeTime(String(e.occurred_at)) : ""}
            {e.source ? ` · ${String(e.source)}` : ""}
          </p>
        </div>
      ))}
      {!items.length && <p className="text-sm text-muted">{empty}</p>}
    </div>
  );
}

export function ApiActivityTab({ detail }: { detail: OrderDetail }) {
  const items = [
    ...(detail.api_activity ?? []),
    ...detail.domain_events.filter((e) =>
      String(e.event_type).match(/stripe|firebase|webhook|email|maps|day_plan|optimize/i)
    ),
  ];
  return <EventListTab items={items} empty="No API activity recorded" />;
}

export function AuditTab({ detail }: { detail: OrderDetail }) {
  return (
    <div className="space-y-2">
      {detail.audit_log.map((a, i) => (
        <div key={i} className="rounded-lg border border-primary/10 px-3 py-2 text-sm">
          <p className="font-medium">{String(a.action)}</p>
          <p className="text-xs text-muted">
            {a.created_at ? relativeTime(String(a.created_at)) : ""}
            {a.actor_user_id ? ` · ${String(a.actor_user_id)}` : ""}
          </p>
          {a.payload &&
          typeof a.payload === "object" &&
          Object.keys(a.payload as object).length > 0 ? (
            <pre className="mt-1 overflow-auto rounded bg-gray-bg p-2 text-[10px]">
              {JSON.stringify(a.payload, null, 2)}
            </pre>
          ) : null}
        </div>
      ))}
      {!detail.audit_log.length && <p className="text-sm text-muted">No audit entries</p>}
    </div>
  );
}

export function SystemSection({ detail }: { detail: OrderDetail }) {
  return (
    <div className="space-y-8">
      <SectionBlock title="Automation">
        <EventListTab items={detail.automation ?? []} empty="No automation events" />
      </SectionBlock>
      <SectionBlock title="API activity">
        <ApiActivityTab detail={detail} />
      </SectionBlock>
      <SectionBlock title="Audit log">
        <AuditTab detail={detail} />
      </SectionBlock>
    </div>
  );
}
