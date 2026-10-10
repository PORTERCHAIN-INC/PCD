"use client";

import { useState } from "react";
import { cn } from "@porterchain/ui/utils";
import { useApiData } from "@/hooks/useApiData";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { ops } from "@/lib/operations";
import {
  dispatch,
  EXCEPTIONS_PAGE,
  pageLabel,
  type DispatchExceptionItem,
  type ExceptionFix,
} from "@/lib/dispatch";

const SEVERITY_DOT: Record<string, string> = {
  critical: "bg-red-600",
  high: "bg-amber-500",
  medium: "bg-secondary",
  low: "bg-slate-400",
};

const LABEL: Record<string, string> = {
  late: "Late",
  at_risk: "At risk of late",
  unassigned: "Unassigned 15+ min",
  failed: "Failed delivery",
  damaged: "Damaged",
  lost: "Lost",
  return: "Return to sender",
  claim: "Claim open",
  margin: "Below margin floor",
};

const money = (c: number) => `$${(c / 100).toFixed(2)}`;

function label(i: DispatchExceptionItem): string {
  if (i.kind === "exception") {
    if (i.type === "DRIVER_TIMEOUT") return "No driver accepted";
    if (i.type === "package_short_at_drop") return "Short delivery — box missing at drop";
    if (i.type === "package_missing") return "Box missing at pickup";
    return i.type
      .toLowerCase()
      .replaceAll("_", " ")
      .replace(/^\w/, (c) => c.toUpperCase());
  }
  return LABEL[i.kind] ?? i.type;
}

function Row({
  item,
  onOpenOrder,
  onChanged,
}: {
  item: DispatchExceptionItem;
  onOpenOrder: (id: string) => void;
  onChanged: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<ExceptionFix | null>(null);
  const [top, ...more] = item.fixes ?? [];
  const canOffer = !top && (item.kind === "unassigned" || item.type === "DRIVER_TIMEOUT");
  const apply = (fix: ExceptionFix) =>
    run(
      (t) => dispatch.applyFix(t, item, fix),
      fix.action === "reroute" ? "Re-plan drafted — commit it on Plan" : "Applied"
    );

  const run = async (fn: (t: string) => Promise<unknown>, done: string) => {
    setBusy(true);
    try {
      await fn(await getApiToken());
      setNote(done);
      onChanged();
    } catch (e) {
      setNote(e instanceof Error ? e.message : "Failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3">
      <span
        className={cn("h-2.5 w-2.5 shrink-0 rounded-full", SEVERITY_DOT[item.severity])}
        aria-hidden
      />
      <span className="sr-only">{item.severity}</span>
      <button
        type="button"
        onClick={() => onOpenOrder(item.order_id)}
        className="min-w-0 flex-1 text-left"
      >
        <span className="block truncate text-sm font-semibold text-primary">{label(item)}</span>
        <span className="block truncate text-xs text-muted">
          {item.order_number} · {item.state.replaceAll("_", " ").toLowerCase()}
          {item.age_min != null ? ` · ${item.age_min}m` : ""}
          {item.eta
            ? ` · ETA ${new Date(item.eta).toLocaleTimeString("en-CA", { hour: "2-digit", minute: "2-digit" })}`
            : ""}
          {item.kind === "margin" && item.price_cents != null && item.cost_cents != null
            ? ` · ${money(item.price_cents)} price · ${money(item.cost_cents)} cost · ${item.margin_pct}% vs ${item.floor_pct}% floor`
            : ""}
        </span>
        {top && (
          <span className="mt-0.5 block truncate text-xs text-secondary">
            Suggested: {top.label} — {top.why}
          </span>
        )}
      </button>
      <div className="flex shrink-0 gap-2">
        {top && (
          <button
            type="button"
            disabled={busy}
            onClick={() => (confirm === top ? apply(top) : setConfirm(top))}
            className="min-h-10 rounded-xl bg-secondary px-3 text-sm font-semibold text-white disabled:opacity-50"
          >
            {confirm === top ? "Confirm" : "Apply"}
          </button>
        )}
        {more.length > 0 && (
          <details className="relative">
            <summary className="flex min-h-10 cursor-pointer list-none items-center rounded-xl border border-primary/15 px-3 text-sm font-medium text-primary">
              More
            </summary>
            <div className="absolute right-0 z-10 mt-1 w-60 rounded-xl border border-primary/10 bg-white p-1 shadow-lg">
              {more.map((f) => (
                <button
                  key={f.action}
                  type="button"
                  disabled={busy}
                  onClick={() => (confirm === f ? apply(f) : setConfirm(f))}
                  className="block w-full rounded-lg px-3 py-2 text-left text-sm text-primary hover:bg-primary/5"
                >
                  {confirm === f ? `Confirm: ${f.label}` : f.label}
                  <span className="block text-xs text-muted">{f.why}</span>
                </button>
              ))}
            </div>
          </details>
        )}
        {canOffer && (
          <button
            type="button"
            disabled={busy}
            onClick={() => run((t) => dispatch.offer(t, item.order_id), "Offered")}
            className="min-h-10 rounded-xl bg-secondary px-3 text-sm font-semibold text-white disabled:opacity-50"
          >
            Offer
          </button>
        )}
        {item.exception_id && (
          <button
            type="button"
            disabled={busy}
            onClick={() => run((t) => ops.resolveException(t, item.exception_id!), "Resolved")}
            className="min-h-10 rounded-xl border border-primary/15 px-3 text-sm font-medium text-primary disabled:opacity-50"
          >
            Resolve
          </button>
        )}
      </div>
      {note && <p className="w-full pl-6 text-xs text-primary">{note}</p>}
    </li>
  );
}

export function ExceptionsQueue({
  tick,
  onOpenOrder,
  onChanged,
}: {
  tick: number;
  onOpenOrder: (id: string) => void;
  onChanged: () => void;
}) {
  const [offset, setOffset] = useState(0);
  const { data, loading, error } = useApiData(
    (t) => dispatch.exceptions(t, offset),
    [tick, offset],
    {
      key: `dispatch-exceptions-${offset}`,
    }
  );
  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const label = pageLabel(offset, items.length, total);
  return (
    <section className="rounded-2xl border border-primary/10 bg-white">
      <header className="flex flex-wrap items-baseline justify-between gap-2 px-4 pt-4 pb-2">
        <h2 className="text-base font-semibold text-primary">Exceptions</h2>
        <span className="flex gap-3 text-xs tabular-nums text-muted">
          <span>{data?.counts.critical ?? 0} critical</span>
          <span>{data?.counts.high ?? 0} high</span>
          <span>{data?.counts.medium ?? 0} medium</span>
        </span>
      </header>
      {data?.eta === "unavailable" && (
        <p className="px-4 pb-2 text-xs text-amber-800">
          Live ETAs unavailable — late/at-risk not checked.
        </p>
      )}
      {error && <p className="px-4 pb-3 text-sm text-red-700">{error}</p>}
      {loading && !data ? <p className="px-4 pb-4 text-sm text-muted">Loading…</p> : null}
      {!loading && items.length === 0 && !error ? (
        <p className="px-4 pb-6 text-sm text-muted">Clear. Nothing needs you.</p>
      ) : null}
      <ul className="divide-y divide-primary/5">
        {items.map((i) => (
          <Row key={i.id} item={i} onOpenOrder={onOpenOrder} onChanged={onChanged} />
        ))}
      </ul>
      {label ? (
        <footer className="flex items-center justify-between gap-2 border-t border-primary/5 px-4 py-3 text-sm">
          <span className="tabular-nums text-muted">{label}</span>
          <span className="flex gap-2">
            <button
              type="button"
              disabled={offset === 0}
              onClick={() => setOffset((o) => Math.max(0, o - EXCEPTIONS_PAGE))}
              className="min-h-11 rounded-xl px-3 font-semibold text-primary disabled:opacity-40"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={offset + items.length >= total}
              onClick={() => setOffset((o) => o + EXCEPTIONS_PAGE)}
              className="min-h-11 rounded-xl px-3 font-semibold text-primary disabled:opacity-40"
            >
              Next
            </button>
          </span>
        </footer>
      ) : null}
    </section>
  );
}
