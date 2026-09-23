"use client";

import { useEffect, useMemo, useState } from "react";
import { RotateCcw, Save } from "lucide-react";
import { Button, Field, Input, Textarea } from "@/components/crm/primitives";
import { SECTION_DESCRIPTIONS } from "@/lib/settings-metadata";
import type { VehicleClassConfig } from "@/lib/settings";
import { BindingBadge, SettingsCard, SettingsPageHeader } from "../ui/SettingsPrimitives";
import CustomerPricingPanel from "./CustomerPricingPanel";
import FsaRatesCard from "./FsaRatesCard";

export type GtaVehicleRates = {
  base_price: number;
  extra_km_rate: number;
  extra_pick_fee: number;
  extra_drop_fee: number;
};

export type GtaPricingConfig = {
  base_km_limit: number;
  downtown_fee_cad: number;
  upper_zone_fee_cad: number;
  vehicles: Record<string, GtaVehicleRates>;
};

type TaxConfig = { hst_percent: number; tax_included: boolean };
type FuelConfig = {
  surcharge_percent: number;
  base_fuel_price_cents: number;
  current_fuel_price_cents: number;
};
type RateCardConfig = {
  liftgate_cents: number;
  extra_stop_cents: number;
  weight_threshold_kg: number;
  weight_cents_per_kg: number;
};

const DEFAULT_RATES: GtaVehicleRates = {
  base_price: 50,
  extra_km_rate: 1.5,
  extra_pick_fee: 20,
  extra_drop_fee: 15,
};

function num(v: unknown, fallback: number): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function normalizeGta(raw: unknown, catalogIds: string[]): GtaPricingConfig {
  const src = typeof raw === "object" && raw !== null ? (raw as Record<string, unknown>) : {};
  const vehiclesRaw =
    typeof src.vehicles === "object" && src.vehicles !== null
      ? (src.vehicles as Record<string, Record<string, unknown>>)
      : {};
  const vehicles: Record<string, GtaVehicleRates> = {};
  const storedIds = Object.keys(vehiclesRaw);
  const ids = storedIds.length
    ? storedIds
    : catalogIds.length
      ? catalogIds
      : ["sedan", "suv", "pickup", "cargo_van", "sprinter_van", "box_truck"];
  for (const id of ids) {
    const row = vehiclesRaw[id] ?? {};
    vehicles[id] = {
      base_price: num(row.base_price, DEFAULT_RATES.base_price),
      extra_km_rate: num(row.extra_km_rate, DEFAULT_RATES.extra_km_rate),
      extra_pick_fee: num(row.extra_pick_fee, DEFAULT_RATES.extra_pick_fee),
      extra_drop_fee: num(row.extra_drop_fee, DEFAULT_RATES.extra_drop_fee),
    };
  }
  return {
    base_km_limit: num(src.base_km_limit, 20),
    downtown_fee_cad: num(src.downtown_fee_cad, 25),
    upper_zone_fee_cad: num(src.upper_zone_fee_cad, 15),
    vehicles,
  };
}

function normalizeRateCard(raw: unknown): RateCardConfig {
  const src = typeof raw === "object" && raw !== null ? (raw as Record<string, unknown>) : {};
  return {
    liftgate_cents: num(src.liftgate_cents, 4500),
    extra_stop_cents: num(src.extra_stop_cents, 0),
    weight_threshold_kg: num(src.weight_threshold_kg, 50),
    weight_cents_per_kg: num(src.weight_cents_per_kg, 0),
  };
}

type Props = {
  data: unknown;
  taxData?: unknown;
  fuelData?: unknown;
  rateCardData?: unknown;
  vehicleCatalog?: unknown;
  customerData?: unknown;
  saving?: boolean;
  onSaveGta: (value: GtaPricingConfig, reason: string) => Promise<void>;
  onSaveTax: (value: TaxConfig, reason: string) => Promise<void>;
  onSaveFuel: (value: FuelConfig, reason: string) => Promise<void>;
  onSaveRateCard: (value: RateCardConfig, reason: string) => Promise<void>;
  onSaveCustomer?: (value: unknown, reason: string) => Promise<void>;
};

export default function PricingPanel({
  data,
  taxData,
  fuelData,
  rateCardData,
  vehicleCatalog,
  customerData,
  saving,
  onSaveGta,
  onSaveTax,
  onSaveFuel,
  onSaveRateCard,
  onSaveCustomer,
}: Props) {
  const catalog = useMemo(() => {
    if (!Array.isArray(vehicleCatalog)) return [] as VehicleClassConfig[];
    return vehicleCatalog.filter(
      (v): v is VehicleClassConfig => typeof v === "object" && v !== null && "id" in v
    );
  }, [vehicleCatalog]);
  const catalogIds = useMemo(() => catalog.map((v) => v.id), [catalog]);
  const labels = Object.fromEntries(catalog.map((v) => [v.id, v.label]));

  const initial = useMemo(() => normalizeGta(data, catalogIds), [data, catalogIds]);
  const [config, setConfig] = useState(initial);
  const [tax, setTax] = useState<TaxConfig>(() => ({
    hst_percent: num((taxData as { hst_percent?: number })?.hst_percent, 0),
    tax_included: Boolean((taxData as { tax_included?: boolean })?.tax_included),
  }));
  const [fuel, setFuel] = useState<FuelConfig>(() => ({
    surcharge_percent: num((fuelData as { surcharge_percent?: number })?.surcharge_percent, 0),
    base_fuel_price_cents: num(
      (fuelData as { base_fuel_price_cents?: number })?.base_fuel_price_cents,
      145
    ),
    current_fuel_price_cents: num(
      (fuelData as { current_fuel_price_cents?: number })?.current_fuel_price_cents,
      158
    ),
  }));
  const [rateCard, setRateCard] = useState<RateCardConfig>(() => normalizeRateCard(rateCardData));
  const [reason, setReason] = useState("");
  const [audience, setAudience] = useState<"merchant" | "customer">("customer");
  const [dirty, setDirty] = useState<"gta" | "tax" | "fuel" | "card" | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    setConfig(initial);
    setDirty(null);
  }, [initial]);

  const preview = useMemo(() => {
    const v = config.vehicles.cargo_van ?? config.vehicles.sedan ?? DEFAULT_RATES;
    const km = 28;
    const extra = Math.max(0, km - config.base_km_limit) * v.extra_km_rate;
    return (v.base_price + extra + config.downtown_fee_cad).toFixed(2);
  }, [config]);

  const missing = catalogIds.filter((id) => !config.vehicles[id]);

  async function save() {
    if (!reason.trim()) {
      setToast("Change reason required for pricing");
      return;
    }
    try {
      if (dirty === "tax") await onSaveTax(tax, reason.trim());
      else if (dirty === "fuel") await onSaveFuel(fuel, reason.trim());
      else if (dirty === "card") await onSaveRateCard(rateCard, reason.trim());
      else await onSaveGta(config, reason.trim());
      setDirty(null);
      setReason("");
      setToast("Saved — retail quotes use the new rates");
    } catch (e) {
      setToast(e instanceof Error ? e.message : "Save failed");
    }
  }

  return (
    <div className="space-y-6">
      <SettingsPageHeader
        title="Pricing"
        description={SECTION_DESCRIPTIONS.pricing}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <BindingBadge effect="wired" />
            <Button
              variant="outline"
              onClick={() => {
                setConfig(initial);
                setDirty(null);
              }}
            >
              <RotateCcw className="h-4 w-4" /> Reset
            </Button>
            <Button
              variant="primary"
              disabled={audience === "customer" || !dirty || saving}
              onClick={() => void save()}
            >
              <Save className="h-4 w-4" /> {saving ? "Saving…" : "Save"}
            </Button>
          </div>
        }
      />

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
      {audience === "customer" && onSaveCustomer && (
        <CustomerPricingPanel data={customerData} saving={saving} onSave={onSaveCustomer} />
      )}
      {audience === "customer" ? null : (
        <>
          {toast && <p className="text-sm text-secondary">{toast}</p>}
          {missing.length > 0 && (
            <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              Missing rates for: {missing.join(", ")}. Add rows or disable those classes under
              Vehicles.
            </p>
          )}

          <div className="grid gap-3 sm:grid-cols-3">
            <Field label="Base km included">
              <Input
                type="number"
                value={config.base_km_limit}
                onChange={(e) => {
                  setConfig({ ...config, base_km_limit: num(e.target.value, 20) });
                  setDirty("gta");
                }}
              />
            </Field>
            <Field label="Downtown fee (CAD)">
              <Input
                type="number"
                value={config.downtown_fee_cad}
                onChange={(e) => {
                  setConfig({ ...config, downtown_fee_cad: num(e.target.value, 0) });
                  setDirty("gta");
                }}
              />
            </Field>
            <Field label="Upper zone fee (CAD)">
              <Input
                type="number"
                value={config.upper_zone_fee_cad}
                onChange={(e) => {
                  setConfig({ ...config, upper_zone_fee_cad: num(e.target.value, 0) });
                  setDirty("gta");
                }}
              />
            </Field>
          </div>

          <SettingsCard
            title="GTA vehicle matrix"
            description={`Sample 28 km downtown cargo/sedan ≈ $${preview} CAD (preview only)`}
          >
            <div className="ops-table-scroll">
              <table className="w-full min-w-[36rem] text-left text-sm">
                <thead>
                  <tr className="border-b border-primary/10 text-xs uppercase text-muted">
                    <th className="py-2 pr-2">Vehicle</th>
                    <th className="py-2 pr-2">Base</th>
                    <th className="py-2 pr-2">Extra km</th>
                    <th className="py-2 pr-2">Extra pick</th>
                    <th className="py-2">Extra drop</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.keys(config.vehicles).map((id) => {
                    const row = config.vehicles[id]!;
                    return (
                      <tr key={id} className="border-b border-primary/5">
                        <td className="py-2 pr-2 font-medium">{labels[id] ?? id}</td>
                        {(
                          [
                            "base_price",
                            "extra_km_rate",
                            "extra_pick_fee",
                            "extra_drop_fee",
                          ] as const
                        ).map((field) => (
                          <td key={field} className="py-2 pr-2">
                            <Input
                              type="number"
                              step="0.01"
                              value={row[field]}
                              onChange={(e) => {
                                const n = num(e.target.value, row[field]);
                                setConfig({
                                  ...config,
                                  vehicles: {
                                    ...config.vehicles,
                                    [id]: { ...row, [field]: n },
                                  },
                                });
                                setDirty("gta");
                              }}
                            />
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-xs text-muted">
              Linked:{" "}
              <button
                type="button"
                className="font-medium text-secondary"
                onClick={() =>
                  window.dispatchEvent(new CustomEvent("settings-navigate", { detail: "vehicles" }))
                }
              >
                Vehicle classes
              </button>
            </p>
          </SettingsCard>

          <FsaRatesCard vehicleCatalog={catalog} />

          <SettingsCard
            title="Liftgate, extra stop, and weight"
            description="Platform defaults on every quote. Dollars here, cents in the API. Driver payout stays off this screen."
          >
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Liftgate (CAD)">
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={(rateCard.liftgate_cents / 100).toFixed(2)}
                  onChange={(e) => {
                    setRateCard({
                      ...rateCard,
                      liftgate_cents: Math.max(0, Math.round(num(e.target.value, 0) * 100)),
                    });
                    setDirty("card");
                  }}
                />
              </Field>
              <Field label="Extra stop (CAD)">
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={(rateCard.extra_stop_cents / 100).toFixed(2)}
                  onChange={(e) => {
                    setRateCard({
                      ...rateCard,
                      extra_stop_cents: Math.max(0, Math.round(num(e.target.value, 0) * 100)),
                    });
                    setDirty("card");
                  }}
                />
              </Field>
              <Field label="Weight threshold (kg)">
                <Input
                  type="number"
                  step="0.1"
                  min="0"
                  value={rateCard.weight_threshold_kg}
                  onChange={(e) => {
                    setRateCard({
                      ...rateCard,
                      weight_threshold_kg: Math.max(0, num(e.target.value, 0)),
                    });
                    setDirty("card");
                  }}
                />
              </Field>
              <Field label="Over-weight (CAD / kg)">
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={(rateCard.weight_cents_per_kg / 100).toFixed(2)}
                  onChange={(e) => {
                    setRateCard({
                      ...rateCard,
                      weight_cents_per_kg: Math.max(0, Math.round(num(e.target.value, 0) * 100)),
                    });
                    setDirty("card");
                  }}
                />
              </Field>
            </div>
          </SettingsCard>

          <SettingsCard title="Tax (HST)" description="Wired into pricing engine tax config">
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="HST %">
                <Input
                  type="number"
                  step="0.1"
                  value={tax.hst_percent}
                  onChange={(e) => {
                    setTax({ ...tax, hst_percent: num(e.target.value, 0) });
                    setDirty("tax");
                  }}
                />
              </Field>
            </div>
          </SettingsCard>

          <SettingsCard title="Fuel surcharge" description="Wired into pricing engine fuel config">
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="Surcharge %">
                <Input
                  type="number"
                  step="0.1"
                  value={fuel.surcharge_percent}
                  onChange={(e) => {
                    setFuel({ ...fuel, surcharge_percent: num(e.target.value, 0) });
                    setDirty("fuel");
                  }}
                />
              </Field>
              <Field label="Base fuel ($/L)">
                <Input
                  type="number"
                  step="0.01"
                  value={fuel.base_fuel_price_cents / 100}
                  onChange={(e) => {
                    setFuel({
                      ...fuel,
                      base_fuel_price_cents: Math.round(num(e.target.value, 0) * 100),
                    });
                    setDirty("fuel");
                  }}
                />
              </Field>
              <Field label="Current fuel ($/L)">
                <Input
                  type="number"
                  step="0.01"
                  value={fuel.current_fuel_price_cents / 100}
                  onChange={(e) => {
                    setFuel({
                      ...fuel,
                      current_fuel_price_cents: Math.round(num(e.target.value, 0) * 100),
                    });
                    setDirty("fuel");
                  }}
                />
              </Field>
            </div>
          </SettingsCard>

          <label className="block text-sm">
            <span className="text-xs font-medium text-muted">Change reason (required)</span>
            <Textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={2}
              className="mt-1"
              placeholder="e.g. Q3 GTA rate adjustment"
            />
          </label>
        </>
      )}
    </div>
  );
}
