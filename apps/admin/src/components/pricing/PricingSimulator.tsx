"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Calculator } from "lucide-react";
import { formatCents } from "@porterchain/ui/utils";
import { VEHICLE_CLASSES, type SimulateRequest, type SimulateResult } from "@/lib/pricing";
import { Button } from "@/components/crm/primitives";

type Props = {
  onSimulate: (body: SimulateRequest) => Promise<SimulateResult>;
};

export default function PricingSimulator({ onSimulate }: Props) {
  const [pickup, setPickup] = useState("Toronto, ON");
  const [dropoff, setDropoff] = useState("Mississauga, ON");
  const [vehicle, setVehicle] = useState("sedan");
  const [merchantId, setMerchantId] = useState("");
  const [promo, setPromo] = useState("");
  const [weight, setWeight] = useState("");
  const [distance, setDistance] = useState("12000");
  const [result, setResult] = useState<SimulateResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    setLoading(true);
    try {
      const res = await onSimulate({
        pickup: { formatted: pickup },
        dropoff: { formatted: dropoff },
        vehicle_class: vehicle,
        merchant_id: merchantId || undefined,
        promo_code: promo || undefined,
        weight_kg: weight ? Number(weight) : undefined,
        distance_meters: distance ? Number(distance) : undefined,
        service_type: "same_day",
        channel: merchantId ? "merchant" : "retail",
      });
      setResult(res);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-3">
        <h3 className="flex items-center gap-2 font-semibold text-primary">
          <Calculator className="h-5 w-5 text-secondary" /> Pricing sandbox
        </h3>
        <label className="block text-xs font-bold uppercase text-muted">Pickup</label>
        <input value={pickup} onChange={(e) => setPickup(e.target.value)} className="w-full rounded-xl border border-primary/10 px-3 py-2 text-sm" />
        <label className="block text-xs font-bold uppercase text-muted">Dropoff</label>
        <input value={dropoff} onChange={(e) => setDropoff(e.target.value)} className="w-full rounded-xl border border-primary/10 px-3 py-2 text-sm" />
        <label className="block text-xs font-bold uppercase text-muted">Vehicle</label>
        <select value={vehicle} onChange={(e) => setVehicle(e.target.value)} className="w-full rounded-xl border border-primary/10 px-3 py-2 text-sm">
          {VEHICLE_CLASSES.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
        <div className="grid grid-cols-2 gap-2">
          <input placeholder="Weight kg" value={weight} onChange={(e) => setWeight(e.target.value)} className="rounded-xl border border-primary/10 px-3 py-2 text-sm" />
          <input placeholder="Distance m" value={distance} onChange={(e) => setDistance(e.target.value)} className="rounded-xl border border-primary/10 px-3 py-2 text-sm" />
        </div>
        <input placeholder="Merchant ID (optional)" value={merchantId} onChange={(e) => setMerchantId(e.target.value)} className="w-full rounded-xl border border-primary/10 px-3 py-2 text-sm" />
        <input placeholder="Promo code" value={promo} onChange={(e) => setPromo(e.target.value)} className="w-full rounded-xl border border-primary/10 px-3 py-2 text-sm" />
        <Button variant="primary" disabled={loading} onClick={() => void run()}>
          {loading ? "Calculating…" : "Preview quote"}
        </Button>
      </div>

      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="rounded-2xl border border-primary/10 bg-gray-bg/30 p-4">
        {!result ? (
          <p className="text-sm text-muted">Server-side quote preview — all rules applied by the Pricing Engine.</p>
        ) : (
          <div className="space-y-2">
            <p className="text-2xl font-bold text-primary">{formatCents(result.final_cents)}</p>
            {result.items.map((line) => (
              <div key={line.code} className="flex justify-between text-sm">
                <span className="text-muted">{line.label}</span>
                <span className="font-medium">{formatCents(line.amount_cents)}</span>
              </div>
            ))}
            <div className="mt-3 border-t border-primary/10 pt-2 text-xs text-muted">
              Tax {formatCents(result.tax_cents)} · Discount {formatCents(result.discount_cents)}
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
}
