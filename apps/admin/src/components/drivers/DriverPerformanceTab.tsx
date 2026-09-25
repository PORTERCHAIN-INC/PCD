"use client";

import type { DriverDetail } from "@/lib/drivers";
import { SectionCard } from "@/components/crm/primitives";
import { Detail } from "@/components/drivers/DriverDetailShared";

export function PerformanceTab({ d }: { d: DriverDetail }) {
  const m = d.metrics;
  const bars = [
    { label: "Acceptance rate", value: m.acceptance_rate },
    { label: "Completion rate", value: m.completion_rate },
    { label: "On-time %", value: m.on_time_percent },
  ];
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <SectionCard title="Performance">
        <div className="space-y-4 p-5">
          {bars.map((b) => (
            <div key={b.label}>
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="text-primary">{b.label}</span>
                <span className="font-semibold text-primary">{b.value}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-gray-bg">
                <div
                  className="h-full rounded-full bg-secondary"
                  style={{ width: `${Math.min(100, b.value)}%` }}
                />
              </div>
            </div>
          ))}
          <div className="flex items-center justify-between pt-2 text-sm">
            <span className="text-muted">Cancellation rate</span>
            <span className="font-semibold text-red-600">{m.cancellation_rate}%</span>
          </div>
        </div>
      </SectionCard>
      <SectionCard title="Ratings & quality">
        <dl className="grid grid-cols-2 gap-4 p-5">
          <Detail
            label="Customer rating"
            value={d.rating != null ? `${d.rating.toFixed(1)} / 5` : null}
          />
          <Detail label="Lifetime orders" value={String(m.lifetime_orders)} />
          <Detail label="Lifetime completed" value={String(m.lifetime_completed)} />
          <Detail label="Open incidents" value={String(m.incidents)} />
        </dl>
      </SectionCard>
    </div>
  );
}
