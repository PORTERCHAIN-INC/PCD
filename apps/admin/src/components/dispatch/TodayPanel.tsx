"use client";

import { useState } from "react";
import { ChevronRight, Send, Truck } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useApiData } from "@/hooks/useApiData";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { ops, type QueueOrder } from "@/lib/operations";
import { dispatch, money, type Recommendation } from "@/lib/dispatch";

function waitingMin(created: string | null): number | null {
  if (!created) return null;
  return Math.max(0, Math.round((Date.now() - new Date(created).getTime()) / 60000));
}

function RecommendRow({
  order,
  onOpenOrder,
  onChanged,
}: {
  order: QueueOrder;
  onOpenOrder: (id: string) => void;
  onChanged: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const [open, setOpen] = useState(false);
  const [rec, setRec] = useState<Recommendation | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const wait = waitingMin(order.created_at);

  const load = async () => {
    setOpen((o) => !o);
    if (rec) return;
    setBusy("load");
    try {
      setRec(await dispatch.recommend(await getApiToken(), order.id));
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Could not load recommendation");
    } finally {
      setBusy(null);
    }
  };

  const offer = async () => {
    setBusy("offer");
    setMsg(null);
    try {
      const res = await dispatch.offer(await getApiToken(), order.id);
      setMsg(
        res.offer
          ? `Offered · expires in ${Math.round(res.offer.seconds_left / 60)} min, then passes on`
          : "No eligible driver — added to Exceptions"
      );
      onChanged();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Offer failed");
    } finally {
      setBusy(null);
    }
  };

  const best = rec?.drivers.find((d) => d.driver_id === rec.best_driver_id);

  return (
    <li className="border-b border-primary/5 last:border-0">
      <div className="flex items-center gap-3 px-4 py-3">
        <button
          type="button"
          onClick={load}
          aria-expanded={open}
          className="flex min-w-0 flex-1 items-center gap-3 text-left"
        >
          <ChevronRight
            className={cn("h-4 w-4 shrink-0 text-muted transition-transform", open && "rotate-90")}
          />
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold text-primary">
              {order.order_number}
              {order.merchant ? <span className="font-normal text-muted"> · {order.merchant}</span> : null}
            </span>
            <span className="block truncate text-xs text-muted">
              {order.pickup ?? "—"} → {order.dropoff ?? "—"}
            </span>
          </span>
        </button>
        <span
          className={cn(
            "shrink-0 text-xs font-semibold tabular-nums",
            wait != null && wait >= 15 ? "text-red-700" : "text-muted"
          )}
        >
          {wait == null ? "" : `${wait}m`}
        </span>
        <button
          type="button"
          onClick={offer}
          disabled={busy === "offer"}
          className="inline-flex min-h-10 shrink-0 items-center gap-1.5 rounded-xl bg-secondary px-3 text-sm font-semibold text-white disabled:opacity-50"
        >
          <Send className="h-4 w-4" />
          <span className="hidden sm:inline">Offer</span>
        </button>
      </div>
      {msg ? <p className="px-11 pb-2 text-xs text-primary">{msg}</p> : null}
      {open ? (
        <div className="space-y-2 px-4 pb-4 sm:px-11">
          {busy === "load" && <p className="text-xs text-muted">Ranking drivers…</p>}
          {rec ? (
            <>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
                <span className="inline-flex items-center gap-1.5 font-semibold text-primary">
                  <Truck className="h-4 w-4" />
                  {rec.vehicle ? `${rec.vehicle.label} · ${Math.round(rec.vehicle.fill_pct)}% full` : "No vehicle fits"}
                </span>
                <span className="text-xs text-muted">{rec.vehicle_reason}</span>
                <span className="text-xs text-muted">
                  {rec.load.kg} kg · {rec.load.m3} m³ · {rec.load.boxes} box
                </span>
              </div>
              {rec.matrix !== "valhalla" && (
                <p className="text-xs text-amber-800">
                  Road times unavailable (Valhalla) — drivers listed without time cost.
                </p>
              )}
              <ol className="divide-y divide-primary/5 rounded-xl border border-primary/10">
                {rec.drivers.slice(0, 5).map((d) => (
                  <li key={d.driver_id} className="flex flex-wrap items-center gap-x-3 gap-y-0.5 px-3 py-2 text-sm">
                    <span className={cn("font-medium", d.blocked ? "text-muted line-through" : "text-primary")}>
                      {d.name}
                    </span>
                    {d.driver_id === best?.driver_id && (
                      <span className="rounded-md bg-secondary/10 px-1.5 text-[11px] font-semibold text-secondary">
                        Best
                      </span>
                    )}
                    <span className="text-xs text-muted">
                      {d.blocked
                        ? d.blocked.replaceAll("_", " ")
                        : [
                            d.vehicle_class,
                            d.insertion_minutes != null ? `+${Math.round(d.insertion_minutes)} min` : null,
                            d.fill_after_pct != null ? `${Math.round(d.fill_after_pct)}% full` : null,
                            d.active_jobs ? `${d.active_jobs} active` : null,
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                    </span>
                    <span className="ml-auto text-sm font-semibold tabular-nums text-primary">
                      {d.blocked ? "" : money(d.cost_cents)}
                    </span>
                  </li>
                ))}
                {rec.drivers.length === 0 && (
                  <li className="px-3 py-2 text-xs text-muted">No driver online or on shift.</li>
                )}
              </ol>
              <button
                type="button"
                className="text-xs font-medium text-secondary hover:underline"
                onClick={() => onOpenOrder(order.id)}
              >
                Open order
              </button>
            </>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}

export function TodayPanel({
  tick,
  onOpenOrder,
  onChanged,
}: {
  tick: number;
  onOpenOrder: (id: string) => void;
  onChanged: () => void;
}) {
  const { data, loading, error } = useApiData((t) => ops.queue(t), [tick], { key: "dispatch-today-queue" });
  const rows = data ?? [];
  return (
    <section className="rounded-2xl border border-primary/10 bg-white">
      <header className="flex items-baseline justify-between px-4 pt-4 pb-2">
        <h2 className="text-base font-semibold text-primary">Unassigned</h2>
        <span className="text-sm tabular-nums text-muted">{rows.length}</span>
      </header>
      {error && <p className="px-4 pb-3 text-sm text-red-700">{error}</p>}
      {loading && !data ? <p className="px-4 pb-4 text-sm text-muted">Loading…</p> : null}
      {!loading && rows.length === 0 && !error ? (
        <p className="px-4 pb-6 text-sm text-muted">Nothing waiting. Every order has a driver.</p>
      ) : null}
      <ul>
        {rows.map((o) => (
          <RecommendRow key={o.id} order={o} onOpenOrder={onOpenOrder} onChanged={onChanged} />
        ))}
      </ul>
    </section>
  );
}
