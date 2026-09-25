"use client";

import { DeliveryTimeline } from "@/components/tracking/DeliveryTimeline";
import { orderStateLabel } from "@/lib/catalog";
import { formatDate } from "@/lib/utils";
import { Card } from "./shared";

export function TimelineTab({ timeline }: { timeline: Array<Record<string, unknown>> }) {
  return (
    <Card title="Order timeline">
      <ol className="space-y-3">
        {timeline.length === 0 && <li className="text-muted">No events yet.</li>}
        {timeline.map((ev, i) => (
          <li key={i} className="border-l-2 border-secondary/30 pl-4">
            <p className="font-medium">{String(ev.label ?? ev.event_type)}</p>
            {ev.to_state ? (
              <p className="text-muted">→ {orderStateLabel(String(ev.to_state))}</p>
            ) : null}
            <p className="text-xs text-muted">
              {ev.occurred_at ? formatDate(String(ev.occurred_at)) : ""}
            </p>
          </li>
        ))}
      </ol>
    </Card>
  );
}
