"use client";

import { useApiData } from "@/hooks/useApiData";
import { drivers } from "@/lib/drivers";
import { SectionCard, Spinner } from "@/components/crm/primitives";
import { dateTime, relativeTime, titleCase } from "@/lib/crmFormat";
import { cn } from "@porterchain/ui/utils";

export function TimelineTab({ id }: { id: string }) {
  const { data } = useApiData((t) => drivers.timeline(t, id), [id], {
    key: `driver-timeline-${id}`,
  });
  const tone: Record<string, string> = {
    activity: "bg-secondary",
    order: "bg-violet-500",
    payout: "bg-amber-500",
  };
  return (
    <SectionCard title="Timeline">
      <div className="p-5">
        {(data ?? []).map((e, i) => (
          <div key={i} className="flex gap-3 pb-4 last:pb-0">
            <div className="flex flex-col items-center">
              <span className={cn("h-2.5 w-2.5 rounded-full", tone[e.kind] ?? "bg-slate-400")} />
              {i < (data?.length ?? 0) - 1 && <span className="w-px flex-1 bg-primary/10" />}
            </div>
            <div className="-mt-1">
              <p className="text-sm text-primary">{e.title}</p>
              <p className="text-xs text-muted">
                {titleCase(e.kind)} · {dateTime(e.at)}
              </p>
            </div>
          </div>
        ))}
        {(!data || data.length === 0) && (
          <p className="py-10 text-center text-sm text-muted">No timeline events.</p>
        )}
      </div>
    </SectionCard>
  );
}
