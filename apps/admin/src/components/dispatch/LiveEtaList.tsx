"use client";

import { cn } from "@porterchain/ui/utils";
import { useApiData } from "@/hooks/useApiData";
import { dispatch } from "@/lib/dispatch";

const TONE: Record<string, string> = {
  late: "text-red-700",
  at_risk: "text-amber-800",
  on_time: "text-emerald-800",
  unknown: "text-muted",
};
const TEXT: Record<string, string> = {
  late: "Late",
  at_risk: "At risk",
  on_time: "On time",
  unknown: "No GPS / promise",
};

function hhmm(iso: string | null): string {
  return iso
    ? new Date(iso).toLocaleTimeString("en-CA", { hour: "2-digit", minute: "2-digit" })
    : "—";
}

export function LiveEtaList({
  tick,
  onOpenOrder,
}: {
  tick: number;
  onOpenOrder: (id: string) => void;
}) {
  const { data, loading, error } = useApiData((t) => dispatch.liveEta(t), [tick], {
    key: "dispatch-live-eta",
  });
  const items = data?.items ?? [];
  return (
    <section className="rounded-2xl border border-primary/10 bg-white">
      <header className="flex items-baseline justify-between px-4 pt-4 pb-2">
        <h2 className="text-base font-semibold text-primary">On the road</h2>
        <span className="text-sm tabular-nums text-muted">{items.length}</span>
      </header>
      {error && <p className="px-4 pb-3 text-sm text-red-700">{error}</p>}
      {loading && !data ? <p className="px-4 pb-4 text-sm text-muted">Loading…</p> : null}
      {!loading && items.length === 0 && !error ? (
        <p className="px-4 pb-6 text-sm text-muted">No deliveries in progress.</p>
      ) : null}
      <ul className="divide-y divide-primary/5">
        {items.map((r) => (
          <li key={r.order_id}>
            <button
              type="button"
              onClick={() => onOpenOrder(r.order_id)}
              className="flex w-full items-center gap-3 px-4 py-3 text-left"
            >
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold text-primary">
                  {r.order_number}
                  {r.liftgate && (
                    <span className="ml-1.5 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-900">
                      Liftgate
                    </span>
                  )}
                </span>
                <span className="block truncate text-xs text-muted">
                  {r.state.replaceAll("_", " ").toLowerCase()} · promise {hhmm(r.promise)}
                </span>
              </span>
              <span className="text-right">
                <span className="block text-sm font-semibold tabular-nums text-primary">
                  ETA {hhmm(r.eta)}
                </span>
                <span className={cn("block text-xs font-medium", TONE[r.status])}>
                  {TEXT[r.status]}
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
