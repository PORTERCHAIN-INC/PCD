"use client";

import { useState } from "react";
import { Calculator } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { merchantOps, cad, type QuotePreview } from "@/lib/merchant-ops";
import { Empty, Panel, PrimaryAction, Skeleton, inputClass } from "./ui";

const VERDICT = {
  ok: { tone: "text-emerald-700", label: "Margin OK" },
  below_floor: { tone: "text-amber-800", label: "Below margin floor" },
  below_cost: { tone: "text-red-700", label: "Below driver cost" },
  no_price: { tone: "text-red-700", label: "No price — booking refused" },
} as const;

/** Price any address for this merchant with the live engine and check it against driver cost. */
export function MerchantQuotePreview({ id }: { id: string }) {
  const { getApiToken } = useAdminAuth();
  const [pickup, setPickup] = useState("");
  const [dropoff, setDropoff] = useState("");
  const [weight, setWeight] = useState("");
  const [q, setQ] = useState<QuotePreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const asAddr = (v: string) => {
    const t = v.trim();
    return /^[A-Za-z]\d[A-Za-z]\s?\d[A-Za-z]\d$/.test(t)
      ? { postal: t.toUpperCase(), formatted: t.toUpperCase() }
      : { formatted: t };
  };

  async function run() {
    setBusy(true);
    setErr(null);
    try {
      const t = await getApiToken();
      const w = weight ? Number(weight) : null;
      setQ(
        await merchantOps.quotePreview(t, id, {
          pickup: pickup.trim() ? asAddr(pickup) : undefined,
          dropoff: asAddr(dropoff),
          weight_kg: w != null && Number.isFinite(w) ? w : null,
        })
      );
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Preview failed");
    } finally {
      setBusy(false);
    }
  }

  const v = q ? VERDICT[q.margin.status] : null;
  return (
    <Panel title="Quote preview">
      <form
        className="grid gap-3 sm:grid-cols-[1fr_1fr_7rem_auto] sm:items-end"
        onSubmit={(e) => {
          e.preventDefault();
          if (dropoff.trim()) void run();
        }}
      >
        <label className="block">
          <span className="mb-1.5 block text-sm font-semibold text-primary">Pickup</span>
          <input
            className={inputClass}
            value={pickup}
            onChange={(e) => setPickup(e.target.value)}
            placeholder="Saved pickup"
          />
        </label>
        <label className="block">
          <span className="mb-1.5 block text-sm font-semibold text-primary">Drop-off</span>
          <input
            className={inputClass}
            value={dropoff}
            onChange={(e) => setDropoff(e.target.value)}
            placeholder="M5V 2T6 or address"
            required
          />
        </label>
        <label className="block">
          <span className="mb-1.5 block text-sm font-semibold text-primary">Weight kg</span>
          <input
            className={inputClass}
            inputMode="decimal"
            value={weight}
            onChange={(e) => setWeight(e.target.value.replace(/[^0-9.]/g, ""))}
          />
        </label>
        <PrimaryAction type="submit" disabled={busy || !dropoff.trim()}>
          {busy ? "Pricing…" : "Price it"}
        </PrimaryAction>
      </form>
      {err && (
        <p role="alert" className="mt-3 text-sm font-semibold text-red-700">
          {err}
        </p>
      )}

      <div className="mt-6 border-t border-primary/5 pt-6">
        {busy && !q ? (
          <div className="space-y-3" aria-busy="true">
            <Skeleton className="h-10 w-40" />
            <Skeleton className="h-4 w-64" />
          </div>
        ) : !q || !v ? (
          <Empty
            icon={<Calculator className="h-6 w-6" aria-hidden />}
            title="Price any drop-off"
            hint="Same engine as booking. Shows what the merchant pays, what the driver costs and the margin."
          />
        ) : (
          <div className="space-y-6">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="text-[11px] font-semibold tracking-[0.14em] text-slate-600 uppercase">
                  Merchant pays · incl. tax
                </p>
                <p className="mt-1 text-4xl font-extrabold tracking-tight text-primary tabular-nums">
                  {cad(q.price.final_cents)}
                </p>
                <p className="mt-1 text-sm text-slate-600">
                  {q.price.pricing_model === "fsa" ? "FSA pricing" : "Distance pricing"}
                  {q.route.distance_km != null ? ` · ${q.route.distance_km} km` : ""}
                  {q.price.price_version ? ` · ${q.price.price_version}` : ""}
                </p>
              </div>
              <p className={cn("text-lg font-extrabold", v.tone)}>{v.label}</p>
            </div>
            <dl className="grid grid-cols-3 gap-4">
              <Num label="Pre-tax" value={cad(q.price.subtotal_cents)} />
              <Num label="Driver cost" value={cad(q.driver_cost.cents)} />
              <Num
                label="Margin"
                value={`${cad(q.margin.margin_cents)}${q.margin.margin_pct != null ? ` · ${q.margin.margin_pct}%` : ""}`}
                bad={q.margin.margin_cents < 0}
              />
            </dl>
            <p className="text-sm text-slate-600">
              Driver cost: {q.driver_cost.basis}. Floor {q.margin.floor_pct}%.
            </p>
            {q.price.lines.length > 0 && (
              <details className="group rounded-2xl border border-primary/10">
                <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between px-4 text-sm font-semibold text-primary">
                  Price lines{" "}
                  <span className="text-slate-600 group-open:hidden">{q.price.lines.length}</span>
                </summary>
                <ul className="divide-y divide-primary/5 border-t border-primary/10 text-sm">
                  {q.price.lines.map((l) => (
                    <li
                      key={`${l.code}-${l.label}`}
                      className="flex justify-between gap-3 px-4 py-2.5"
                    >
                      <span className="text-primary">{l.label}</span>
                      <span className="text-primary tabular-nums">{cad(l.amount_cents)}</span>
                    </li>
                  ))}
                </ul>
              </details>
            )}
            {q.fsa_rows_below_floor.length > 0 && (
              <div className="rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-950">
                <p className="font-bold">
                  {q.fsa_rows_below_floor.length} FSA prices under the floor
                </p>
                <p className="mt-1">
                  {q.fsa_rows_below_floor
                    .slice(0, 6)
                    .map(
                      (r) => `${r.origin_fsa ?? "any"}→${r.dest_fsa ?? "any"} ${cad(r.flat_cents)}`
                    )
                    .join(" · ")}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </Panel>
  );
}

function Num({ label, value, bad }: { label: string; value: string; bad?: boolean }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] font-semibold tracking-[0.14em] text-slate-600 uppercase">
        {label}
      </dt>
      <dd
        className={cn(
          "mt-1 truncate text-xl font-extrabold tabular-nums sm:text-2xl",
          bad ? "text-red-700" : "text-primary"
        )}
      >
        {value}
      </dd>
    </div>
  );
}
