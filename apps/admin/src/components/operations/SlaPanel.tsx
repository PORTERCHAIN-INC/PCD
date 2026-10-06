"use client";

import { cn } from "@porterchain/ui/utils";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useApiData } from "@/hooks/useApiData";
import { ops, type OpsOrder } from "@/lib/operations";
import { Badge, EmptyState, SectionCard } from "@/components/crm/primitives";
import { dateTime, titleCase } from "@/lib/crmFormat";

function SlaRow({ o, onOpen }: { o: OpsOrder; onOpen?: () => void }) {
  return (
    <div
      onClick={onOpen}
      className={cn(
        "flex items-center justify-between px-5 py-3",
        onOpen && "cursor-pointer transition-colors hover:bg-gray-bg/60"
      )}
      title={onOpen ? "Open Order 360" : undefined}
    >
      <div>
        <p className="font-mono text-xs font-semibold text-primary">{o.tracking_number}</p>
        <p className="text-xs text-muted">
          {o.merchant ?? "—"} · {o.driver ?? "Unassigned"} · ETA {o.eta ? dateTime(o.eta) : "—"}
        </p>
      </div>
      <Badge tone="sky">{titleCase(o.state)}</Badge>
    </div>
  );
}

export function SlaPanel({
  tick,
  onOpenOrder,
}: {
  tick: number;
  onOpenOrder: (id: string) => void;
}) {
  const { data } = useApiData((t) => ops.sla(t), [tick], { key: "ops-sla" });
  if (!data) return <PageSkeleton rows={3} />;
  return (
    <div className="grid gap-5 md:grid-cols-2">
      <SectionCard title={`Breached (${data.breached_count})`}>
        <div className="divide-y divide-primary/5">
          {data.breached.map((o) => (
            <SlaRow key={o.id} o={o} onOpen={() => onOpenOrder(o.id)} />
          ))}
          {data.breached.length === 0 && <EmptyState title="No SLA breaches" />}
        </div>
      </SectionCard>
      <SectionCard title={`At risk (${data.at_risk_count})`}>
        <div className="divide-y divide-primary/5">
          {data.at_risk.map((o) => (
            <SlaRow key={o.id} o={o} onOpen={() => onOpenOrder(o.id)} />
          ))}
          {data.at_risk.length === 0 && <EmptyState title="Nothing approaching breach" />}
        </div>
      </SectionCard>
    </div>
  );
}
