"use client";

import { useApiData } from "@/hooks/useApiData";
import { drivers } from "@/lib/drivers";
import { SectionCard, Spinner } from "@/components/crm/primitives";
import { money } from "@/lib/crmFormat";

export function AnalyticsTab({ id }: { id: string }) {
  const { data } = useApiData((t) => drivers.analytics(t, id), [id], {
    key: `driver-analytics-${id}`,
  });
  if (!data) return <Spinner />;
  const max = Math.max(1, ...data.by_month.map((r) => r.orders));
  return (
    <SectionCard title="Orders & revenue by month">
      <div className="space-y-3 p-5">
        {data.by_month.map((r) => (
          <div key={r.month}>
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className="text-primary">
                {r.month}{" "}
                <span className="text-muted">
                  · {r.completed}/{r.orders} completed
                </span>
              </span>
              <span className="font-semibold text-primary">{money(r.revenue_cents)}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-gray-bg">
              <div
                className="h-full rounded-full bg-secondary"
                style={{ width: `${(r.orders / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
        {data.by_month.length === 0 && (
          <p className="py-6 text-center text-sm text-muted">No order history yet.</p>
        )}
      </div>
    </SectionCard>
  );
}
