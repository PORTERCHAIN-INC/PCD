"use client";

import { formatDate } from "@/lib/utils";

type Event = Record<string, unknown>;

export function DeliveryTimeline({ events }: { events: Event[] }) {
  if (!events.length) {
    return <p className="text-sm text-muted">No timeline events yet.</p>;
  }

  return (
    <ol className="relative space-y-4 border-l border-primary/15 pl-5">
      {events.map((ev, i) => {
        const isLast = i === events.length - 1;
        return (
          <li key={i} className="relative">
            <span
              className={`absolute -left-[1.35rem] top-1 h-2.5 w-2.5 rounded-full ${
                isLast ? "bg-secondary ring-4 ring-secondary/20" : "bg-primary/30"
              }`}
            />
            <p className="font-medium text-primary">{String(ev.label ?? ev.event_type ?? "Event")}</p>
            {ev.to_state ? (
              <p className="text-sm text-muted">Status → {String(ev.to_state).replace(/_/g, " ")}</p>
            ) : null}
            {ev.occurred_at ? (
              <p className="text-xs text-muted">{formatDate(String(ev.occurred_at))}</p>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
