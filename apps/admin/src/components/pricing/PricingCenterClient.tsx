"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Calculator, ExternalLink } from "lucide-react";
import { formatCents } from "@porterchain/ui/utils";
import { Button, Input, SectionCard, Spinner } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { merchants } from "@/lib/merchants";
import { pricingApi, type SimulateQuoteResult } from "@/lib/pricing";

const LINKS = [
  {
    href: "/settings?section=pricing",
    title: "Platform catalog",
    blurb: "GTA matrix, tax, fuel, platform FSA rates — Settings → Pricing.",
  },
  {
    href: "/merchants",
    title: "Merchant deals",
    blurb: "Open a merchant → Pricing (?tab=pricing) for FSA flats or Distance overlays.",
  },
  {
    href: "/finance",
    title: "Billing & invoices",
    blurb: "Invoice detail shows quote lineage (model, lines, waivers).",
  },
  {
    href: "/finance",
    title: "Stripe / COD",
    blurb: "Connect and COD live on merchant Money; settlement surfaces under Finance.",
  },
];

export default function PricingCenterClient() {
  const { getApiToken } = useAdminAuth();
  const { data: merchantRows, loading: merchantsLoading } = useApiData(
    (token) => merchants.list(token, { limit: "100" }),
    [],
    { key: "pricing-center-merchants", staleTime: 60_000 }
  );

  const merchantList = useMemo(() => {
    const rows = Array.isArray(merchantRows) ? merchantRows : [];
    return rows
      .map((m) => ({
        id: String((m as { id?: string }).id || (m as { merchant_id?: string }).merchant_id || ""),
        name: String(
          (m as { company_name?: string }).company_name ||
            (m as { name?: string }).name ||
            "Merchant"
        ),
      }))
      .filter((m) => m.id);
  }, [merchantRows]);

  const [audience, setAudience] = useState<"customer" | "merchant">("customer");
  const [merchantId, setMerchantId] = useState("");
  const [vehicle, setVehicle] = useState("sedan_suv");
  const [km, setKm] = useState("15");
  const [useTypedKm, setUseTypedKm] = useState(false);
  const [destPostal, setDestPostal] = useState("M5V 2T6");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SimulateQuoteResult | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const meters = Math.max(0, Number(km) || 0) * 1000;
      const out = await pricingApi.simulate(await getApiToken(), {
        merchant_id: audience === "customer" ? null : merchantId || null,
        channel: audience === "customer" ? "retail" : "merchant",
        vehicle_class: vehicle,
        distance_meters: meters,
        use_typed_distance: useTypedKm,
        dropoff: { postal: destPostal, lat: 43.6426, lng: -79.3871, formatted: "Toronto, ON" },
        pickup: { postal: "L4W 5N5", lat: 43.589, lng: -79.6441, formatted: "Mississauga, ON" },
      });
      setResult(out);
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : "Simulate failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">Pricing Center</h1>
        <p className="mt-1 text-sm text-muted">
          Commercial hub: catalog, merchant deals, quote simulator, and billing lineage. Does not
          reprice invoices — quotes remain the source of truth.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {LINKS.map((link) => (
          <Link
            key={link.title}
            href={link.href}
            className="rounded-2xl border border-primary/10 bg-white p-5 transition hover:border-secondary/40"
          >
            <p className="flex items-center gap-2 font-semibold text-primary">
              {link.title}
              <ExternalLink className="h-3.5 w-3.5 text-muted" />
            </p>
            <p className="mt-1 text-sm text-muted">{link.blurb}</p>
          </Link>
        ))}
      </div>

      <SectionCard title="Quote simulator">
        <div className="space-y-4 p-5">
          <p className="text-sm text-muted">
            Loads live merchant overlays (FSA / Distance / surcharges). Shows which layer set the
            base.
          </p>
          <div className="flex gap-2">
            <Button
              variant={audience === "customer" ? "primary" : "outline"}
              onClick={() => setAudience("customer")}
            >
              Customer
            </Button>
            <Button
              variant={audience === "merchant" ? "primary" : "outline"}
              onClick={() => setAudience("merchant")}
            >
              Merchant
            </Button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <label className="text-xs font-medium text-primary/70">
              Merchant
              <select
                className="mt-1 w-full rounded-lg border border-primary/15 px-3 py-2 text-sm"
                value={audience === "customer" ? "" : merchantId}
                onChange={(e) => setMerchantId(e.target.value)}
                disabled={audience === "customer" || merchantsLoading}
              >
                <option value="">Retail (no merchant)</option>
                {merchantList.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs font-medium text-primary/70">
              Vehicle
              <select
                className="mt-1 w-full rounded-lg border border-primary/15 px-3 py-2 text-sm"
                value={vehicle}
                onChange={(e) => setVehicle(e.target.value)}
              >
                {(audience === "customer"
                  ? [
                      ["sedan_suv", "Sedan / SUV"],
                      ["cargo_van", "Cargo van"],
                      ["pickup", "Pickup"],
                      ["box_16", "16 ft"],
                      ["box_20", "20 ft"],
                    ]
                  : [
                      ["sedan", "Sedan"],
                      ["suv", "SUV"],
                      ["cargo_van", "Cargo van"],
                      ["sprinter_van", "Sprinter"],
                      ["box_truck", "Box truck"],
                    ]
                ).map(([id, label]) => (
                  <option key={id} value={id}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs font-medium text-primary/70">
              Override kilometers
              <Input
                className="mt-1"
                type="number"
                min="0"
                step="0.1"
                value={km}
                onChange={(e) => setKm(e.target.value)}
              />
              <span className="mt-1 flex items-center gap-2 font-normal">
                <input
                  type="checkbox"
                  checked={useTypedKm}
                  onChange={(e) => setUseTypedKm(e.target.checked)}
                />
                Use typed kilometers instead of the road network
              </span>
            </label>
            <label className="text-xs font-medium text-primary/70">
              Dest postal (FSA)
              <Input
                className="mt-1"
                value={destPostal}
                onChange={(e) => setDestPostal(e.target.value)}
              />
            </label>
          </div>
          <Button variant="primary" disabled={busy} onClick={() => void run()}>
            <Calculator className="h-4 w-4" />
            {busy ? "Simulating…" : "Simulate quote"}
          </Button>
          {error && <p className="text-sm text-red-700">{error}</p>}
          {busy && !result && <Spinner label="Calculating…" />}
          {result && (
            <div className="rounded-xl border border-primary/10 bg-gray-bg/40 p-4">
              <p className="text-sm font-semibold text-primary">{result.what_won}</p>
              <p className="mt-1 text-xs text-muted">
                Model: {result.pricing_model || "—"}
                {result.pricing_model_requested
                  ? ` · requested ${result.pricing_model_requested}`
                  : ""}
              </p>
              <p className="mt-3 text-2xl font-bold text-primary">
                {formatCents(result.final_cents)}
              </p>
              <ul className="mt-3 space-y-1 text-sm">
                {result.items.map((item, i) => (
                  <li key={`${item.code}-${i}`} className="flex justify-between gap-4">
                    <span className="text-muted">{item.label}</span>
                    <span className="font-mono text-primary">{formatCents(item.amount_cents)}</span>
                  </li>
                ))}
              </ul>
              {merchantId && (
                <Link
                  href={`/merchants/${merchantId}?tab=pricing`}
                  className="mt-4 inline-block text-sm font-medium text-secondary underline"
                >
                  Edit this merchant’s pricing
                </Link>
              )}
            </div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
