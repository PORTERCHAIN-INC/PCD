"use client";

import { useApiData } from "@/hooks/useApiData";
import { ops, type UtilizationDriver } from "@/lib/operations";
import { Badge, EmptyState, SectionCard } from "@/components/crm/primitives";
import { titleCase } from "@/lib/crmFormat";
import { PageSkeleton, TableSkeleton } from "@porterchain/ui/loading";

const STATUS_TONE: Record<string, "green" | "amber" | "sky" | "slate" | "red" | "blue"> = {
  idle: "amber",
  busy: "sky",
  available: "green",
  on_break: "blue",
  on_shift_offline: "red",
  offline: "slate",
};

function fmtMinutes(m: number): string {
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  const mins = m % 60;
  return mins ? `${h}h ${mins}m` : `${h}h`;
}

function DriverRow({ d }: { d: UtilizationDriver }) {
  return (
    <tr className="border-b border-primary/5">
      <td className="px-4 py-2 text-sm font-medium text-primary">{d.name}</td>
      <td className="px-4 py-2">
        <Badge tone={STATUS_TONE[d.status] ?? "slate"}>{titleCase(d.status)}</Badge>
      </td>
      <td className="px-4 py-2 text-sm">{d.online ? "Online" : "Offline"}</td>
      <td className="px-4 py-2 text-sm tabular-nums">{d.active_orders}</td>
      <td className="px-4 py-2 text-sm tabular-nums text-muted">{fmtMinutes(d.shift_minutes)}</td>
      <td className="px-4 py-2 text-sm tabular-nums text-muted">{fmtMinutes(d.break_minutes)}</td>
      <td className="px-4 py-2 text-sm tabular-nums">
        {d.utilization_percent}
        <span className="text-muted">%</span>
      </td>
    </tr>
  );
}

export function UtilizationPanel({ tick }: { tick: number }) {
  const { data, loading } = useApiData((t) => ops.utilization(t), [tick], {
    key: "ops-utilization",
  });

  if (loading && !data) {
    return (
      <div className="space-y-3">
        <PageSkeleton rows={2} />
        <TableSkeleton rows={5} />
      </div>
    );
  }
  if (!data) return <EmptyState title="Utilization unavailable" />;

  const s = data.summary;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
        {[
          ["Online", s.online],
          ["On shift", s.on_shift],
          ["Idle", s.idle],
          ["Busy", s.busy],
          ["On break", s.on_break],
          ["Waiting", s.waiting_unassigned],
          ["Active load", s.active_orders],
          ["Staffing gap", s.staffing_gap],
        ].map(([label, value]) => (
          <div
            key={String(label)}
            className="rounded-xl border border-primary/10 bg-gray-bg/40 px-3 py-2"
          >
            <p className="text-[10px] font-medium uppercase tracking-wide text-muted">{label}</p>
            <p className="mt-0.5 text-lg font-semibold tabular-nums text-primary">{value}</p>
          </div>
        ))}
      </div>

      <p className="text-xs text-muted">
        Online source: {data.online_source === "porterchain" ? "PorterChain" : "Last pin"}.
        Utilization % is a load-based estimate (not GPS idle-time) for staffing glance.
        {s.avg_load_per_online > 0 && ` · Avg load/online: ${s.avg_load_per_online}`}
      </p>

      <SectionCard title={`Drivers (${data.drivers.length})`}>
        <div className="ops-table-scroll">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-primary/10 bg-gray-bg/40 text-xs uppercase text-muted">
              <tr>
                <th className="px-4 py-2">Driver</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Presence</th>
                <th className="px-4 py-2">Orders</th>
                <th className="px-4 py-2">Shift</th>
                <th className="px-4 py-2">Break</th>
                <th className="px-4 py-2">Util</th>
              </tr>
            </thead>
            <tbody>
              {data.drivers.map((d) => (
                <DriverRow key={d.id} d={d} />
              ))}
            </tbody>
          </table>
          {data.drivers.length === 0 && <EmptyState title="No approved drivers" />}
        </div>
      </SectionCard>
    </div>
  );
}
