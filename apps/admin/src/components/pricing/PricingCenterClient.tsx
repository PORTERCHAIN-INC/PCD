"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { formatCents } from "@porterchain/ui/utils";
import { Button, Input } from "@/components/crm/primitives";

import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { merchants } from "@/lib/merchants";
import { pricingApi, type MarginEstimates, type SimulateQuoteResult } from "@/lib/pricing";
import { settingsApi } from "@/lib/settings";
import { withStaffStepUp } from "@/lib/staff-step-up";
import AdminPage from "@/components/layout/AdminPage";
import { FinanceNav } from "@/components/finance/FinanceShell";

const VEHICLES: Array<[string, string]> = [
  ["sedan_suv", "Sedan / SUV"],
  ["pickup", "Pickup"],
  ["cargo_van", "Cargo van"],
  ["sprinter_van", "Sprinter"],
  ["box_16", "16 ft"],
  ["box_20", "20 ft"],
];

const MARGIN_TONE: Record<string, string> = {
  ok: "bg-emerald-50 text-emerald-800 border-emerald-200",
  thin: "bg-amber-50 text-amber-800 border-amber-200",
  below_cost: "bg-red-50 text-red-800 border-red-200",
};
const MARGIN_LABEL: Record<string, string> = {
  ok: "Healthy margin",
  thin: "Thin margin",
  below_cost: "Below cost",
};

/** label, key, unit, scale (display = stored / scale) */
const ESTIMATE_FIELDS: Array<[string, keyof MarginEstimates, string, number]> = [
  ["Average speed", "avg_speed_kmh", "km/h", 1],
  ["Minutes per pickup", "pickup_minutes", "min", 1],
  ["Minutes per drop", "drop_minutes", "min", 1],
  ["Unpaid return share", "deadhead_factor", "%", 0.01],
  ["Vehicle cost", "vehicle_cents_per_km", "$/km", 100],
  ["Thin margin below", "thin_margin_pct", "%", 1],
];

const field = "mt-1 w-full rounded-lg border border-primary/15 px-3 py-2 text-sm";

export default function PricingCenterClient() {
  const { getApiToken } = useAdminAuth();
  const { data: merchantRows } = useApiData((t) => merchants.list(t, { limit: "100" }), [], {
    key: "pricing-center-merchants",
    staleTime: 60_000,
  });
  const merchantList = useMemo(
    () =>
      (Array.isArray(merchantRows) ? merchantRows : [])
        .map((m) => {
          const r = m as {
            id?: string;
            merchant_id?: string;
            company_name?: string;
            name?: string;
          };
          return {
            id: String(r.id || r.merchant_id || ""),
            name: String(r.company_name || r.name || "Merchant"),
          };
        })
        .filter((m) => m.id),
    [merchantRows]
  );

  const [merchantId, setMerchantId] = useState("");
  const [vehicle, setVehicle] = useState("cargo_van");
  const [pickup, setPickup] = useState("100 King St W, Toronto, ON M5X 1A9");
  const [drop, setDrop] = useState("L8P 4R5");
  const [parcels, setParcels] = useState("1");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SimulateQuoteResult | null>(null);

  const [showEst, setShowEst] = useState(false);
  const [est, setEst] = useState<MarginEstimates | null>(null);
  const [estMsg, setEstMsg] = useState<string | null>(null);

  const point = (v: string) =>
    /^[A-Za-z]\d[A-Za-z]\s?\d?[A-Za-z]?\d?$/.test(v.trim())
      ? { postal: v.trim(), formatted: "" }
      : { formatted: v.trim() };

  async function run() {
    setBusy(true);
    setError(null);
    try {
      setResult(
        await pricingApi.simulate(await getApiToken(), {
          merchant_id: merchantId || null,
          channel: merchantId ? "merchant" : "retail",
          vehicle_class: vehicle,
          parcel_count: Math.max(1, Number(parcels) || 1),
          pickup: point(pickup),
          dropoff: point(drop),
        })
      );
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : "Simulate failed");
    } finally {
      setBusy(false);
    }
  }

  async function openEstimates() {
    setShowEst((v) => !v);
    if (est) return;
    const cfg = (await settingsApi.config(await getApiToken())) as {
      config?: Record<string, unknown>;
    };
    setEst((cfg.config?.pricing_margin_estimates as MarginEstimates) ?? null);
  }

  async function saveEstimates() {
    if (!est) return;
    setEstMsg(null);
    try {
      const token = await getApiToken();
      await withStaffStepUp(token, () =>
        settingsApi.updateConfig(token, "pricing_margin_estimates", est, "Margin estimates")
      );
      setEstMsg("Saved");
    } catch (e) {
      setEstMsg(e instanceof Error ? e.message : "Save failed");
    }
  }

  const m = result?.margin;

  return (
    <AdminPage>
      <FinanceNav />
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="text-2xl font-bold tracking-tight text-primary">Pricing</h1>
        <nav className="flex flex-wrap gap-3 text-xs text-muted">
          <Link href="/settings?section=pricing" className="hover:text-primary">
            Rates &amp; settings
          </Link>
          <Link href="/merchants" className="hover:text-primary">
            Merchant deals
          </Link>
          <Link href="/finance/invoices" className="hover:text-primary">
            Invoices
          </Link>
        </nav>
      </div>

      <section className="rounded-2xl border border-primary/10 bg-white p-4 sm:p-5">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <label className="text-xs font-medium text-primary/70 lg:col-span-2">
            Pickup (address or postal)
            <Input className="mt-1" value={pickup} onChange={(e) => setPickup(e.target.value)} />
          </label>
          <label className="text-xs font-medium text-primary/70 lg:col-span-2">
            Drop (address or postal)
            <Input className="mt-1" value={drop} onChange={(e) => setDrop(e.target.value)} />
          </label>
          <label className="text-xs font-medium text-primary/70">
            Parcels
            <Input
              className="mt-1"
              type="number"
              min="1"
              value={parcels}
              onChange={(e) => setParcels(e.target.value)}
            />
          </label>
          <label className="text-xs font-medium text-primary/70 lg:col-span-2">
            Merchant
            <select
              className={field}
              value={merchantId}
              onChange={(e) => setMerchantId(e.target.value)}
            >
              <option value="">Retail customer</option>
              {merchantList.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-medium text-primary/70 lg:col-span-2">
            Vehicle
            <select className={field} value={vehicle} onChange={(e) => setVehicle(e.target.value)}>
              {VEHICLES.map(([id, label]) => (
                <option key={id} value={id}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <div className="flex items-end">
            <Button variant="primary" className="w-full" disabled={busy} onClick={() => void run()}>
              {busy ? "Pricing…" : "Price it"}
            </Button>
          </div>
        </div>
        {error && <p className="mt-3 text-sm text-red-700">{error}</p>}

        {result && (
          <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_1fr]">
            <div>
              <p className="text-3xl font-bold text-primary">{formatCents(result.final_cents)}</p>
              <p className="text-xs text-muted">
                {result.what_won} · before tax {formatCents(result.subtotal_cents)}
              </p>
              <ul className="mt-3 divide-y divide-primary/5 text-sm">
                {result.items.map((item, i) => (
                  <li key={`${item.code}-${i}`} className="flex justify-between gap-4 py-1">
                    <span className="text-muted">{item.label}</span>
                    <span className="font-mono text-primary">{formatCents(item.amount_cents)}</span>
                  </li>
                ))}
              </ul>
            </div>
            {m && (
              <div className={`rounded-xl border p-3 text-sm ${MARGIN_TONE[m.status]}`}>
                <p className="font-semibold">
                  {MARGIN_LABEL[m.status]} · {m.margin_pct}%
                  <span className="ml-2 rounded bg-white/60 px-1.5 py-0.5 text-[10px] font-medium uppercase">
                    estimate
                  </span>
                </p>
                <p className="mt-1">{m.explain}</p>
                {result.distance_flag && (
                  <p className="mt-2 font-medium">
                    Distance check: {result.distance_flag.replaceAll("_", " ")}
                  </p>
                )}
              </div>
            )}
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-primary/10 bg-white p-4 sm:p-5">
        <button
          type="button"
          className="text-sm font-semibold text-primary"
          onClick={() => void openEstimates()}
        >
          Cost estimates behind the margin check {showEst ? "▾" : "▸"}
        </button>
        {showEst && (
          <div className="mt-3">
            <p className="text-xs text-muted">
              These are estimates, not your rates. Driver pay ($27/h) comes from the driver pay
              plan. Changing these never changes a price.
            </p>
            {est ? (
              <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                {ESTIMATE_FIELDS.map(([label, key, unit, scale]) => (
                  <label key={key} className="text-xs font-medium text-primary/70">
                    {label} ({unit})
                    <Input
                      className="mt-1"
                      type="number"
                      step="any"
                      value={String(Number(est[key]) / scale)}
                      onChange={(e) => {
                        const v = Number(e.target.value) * scale;
                        setEst({
                          ...est,
                          [key]: key === "vehicle_cents_per_km" ? Math.round(v) : v,
                        });
                      }}
                    />
                  </label>
                ))}
                <div className="col-span-2 flex items-center gap-3 sm:col-span-3 lg:col-span-6">
                  <Button variant="primary" onClick={() => void saveEstimates()}>
                    Save estimates
                  </Button>
                  {estMsg && <span className="text-xs text-muted">{estMsg}</span>}
                </div>
              </div>
            ) : (
              <p className="mt-2 text-xs text-muted">Loading…</p>
            )}
          </div>
        )}
      </section>
    </AdminPage>
  );
}
