import type { DashboardActivity } from "@/lib/api";
import { formatDate } from "@/lib/utils";

interface RecentActivityProps {
  items: DashboardActivity[];
}

export function RecentActivity({ items }: RecentActivityProps) {
  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="text-lg font-semibold text-primary">Recent Activity</h2>
      <ul className="mt-4 space-y-3">
        {items.length === 0 ? (
          <li className="text-sm text-muted">No recent activity.</li>
        ) : (
          items.map((item) => (
            <li key={`${item.kind}-${item.id}`} className="flex gap-3 border-b border-primary/5 pb-3 last:border-0">
              <span
                className={`mt-1 h-2 w-2 shrink-0 rounded-full ${
                  item.kind === "order" ? "bg-secondary" : "bg-primary/40"
                }`}
              />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-primary">{item.title}</p>
                {item.detail && <p className="text-xs text-muted">{item.detail}</p>}
                <p className="mt-0.5 text-xs text-muted">{formatDate(item.occurred_at)}</p>
              </div>
            </li>
          ))
        )}
      </ul>
    </section>
  );
}
