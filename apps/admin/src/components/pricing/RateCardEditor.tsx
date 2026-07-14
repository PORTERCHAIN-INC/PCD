"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/crm/primitives";
import { VEHICLE_CLASSES, type RateCard } from "@/lib/pricing";

type Props = {
  initial: RateCard;
  onSave: (card: RateCard) => Promise<void>;
  title?: string;
  subtitle?: string;
  /** When true, empty numeric fields are allowed (merchant overlay). */
  sparse?: boolean;
};

function num(value: string, fallback = 0): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

export default function RateCardEditor({
  initial,
  onSave,
  title = "System rate card",
  subtitle = "These rates drive every retail and default merchant quote.",
  sparse = false,
}: Props) {
  const [card, setCard] = useState<RateCard>(initial);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setCard({
      ...initial,
      driver_payout_mode: initial.driver_payout_mode ?? "flat",
      driver_flat_per_delivery_cents: initial.driver_flat_per_delivery_cents ?? 850,
      driver_minimum_payout_cents: initial.driver_minimum_payout_cents ?? 0,
    });
  }, [initial]);

  function setField<K extends keyof RateCard>(key: K, value: RateCard[K]) {
    setCard((c) => ({ ...c, [key]: value }));
    setSaved(false);
  }

  function setVehicle(
    code: string,
    field: "per_km_cents" | "minimum_cents" | "surcharge_cents",
    value: number
  ) {
    setCard((c) => ({
      ...c,
      vehicles: {
        ...(c.vehicles || {}),
        [code]: {
          per_km_cents: c.vehicles?.[code]?.per_km_cents ?? 100,
          minimum_cents: c.vehicles?.[code]?.minimum_cents ?? 100,
          surcharge_cents: c.vehicles?.[code]?.surcharge_cents ?? 0,
          [field]: value,
        },
      },
    }));
    setSaved(false);
  }

  async function save() {
    setBusy(true);
    setError(null);
    try {
      await onSave(card);
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  const Field = ({
    label,
    hint,
    value,
    onChange,
    step = "1",
  }: {
    label: string;
    hint?: string;
    value: number | undefined;
    onChange: (n: number) => void;
    step?: string;
  }) => (
    <label className="block text-sm">
      <span className="font-medium text-primary">{label}</span>
      {hint ? <span className="mt-0.5 block text-xs text-muted">{hint}</span> : null}
      <input
        type="number"
        step={step}
        value={value ?? (sparse ? "" : 0)}
        onChange={(e) => onChange(num(e.target.value))}
        className="mt-1 w-full rounded-xl border border-primary/10 px-3 py-2"
      />
    </label>
  );

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-primary">{title}</h3>
          <p className="text-sm text-muted">{subtitle}</p>
        </div>
        <div className="flex items-center gap-2">
          {saved ? <span className="text-xs font-medium text-green-700">Saved</span> : null}
          {error ? <span className="text-xs text-red-600">{error}</span> : null}
          <Button variant="primary" disabled={busy} onClick={() => void save()}>
            {busy ? "Saving…" : "Save rate card"}
          </Button>
        </div>
      </div>

      <section>
        <h4 className="mb-3 text-sm font-bold uppercase tracking-wide text-muted">
          Vehicle rates (CAD cents)
        </h4>
        <div className="overflow-x-auto rounded-xl border border-primary/10">
          <table className="w-full min-w-[520px] text-sm">
            <thead>
              <tr className="border-b bg-primary/[0.02] text-left text-muted">
                <th className="px-3 py-2">Vehicle</th>
                <th className="px-3 py-2">Per km</th>
                <th className="px-3 py-2">Minimum</th>
                <th className="px-3 py-2">Surcharge</th>
              </tr>
            </thead>
            <tbody>
              {VEHICLE_CLASSES.map((code) => {
                const row = card.vehicles?.[code] ?? {
                  per_km_cents: 100,
                  minimum_cents: 100,
                  surcharge_cents: 0,
                };
                return (
                  <tr key={code} className="border-b border-primary/5">
                    <td className="px-3 py-2 font-mono text-xs">{code}</td>
                    <td className="px-3 py-2">
                      <input
                        type="number"
                        className="w-24 rounded-lg border border-primary/10 px-2 py-1"
                        value={row.per_km_cents}
                        onChange={(e) => setVehicle(code, "per_km_cents", num(e.target.value))}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="number"
                        className="w-24 rounded-lg border border-primary/10 px-2 py-1"
                        value={row.minimum_cents}
                        onChange={(e) => setVehicle(code, "minimum_cents", num(e.target.value))}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="number"
                        className="w-24 rounded-lg border border-primary/10 px-2 py-1"
                        value={row.surcharge_cents}
                        onChange={(e) => setVehicle(code, "surcharge_cents", num(e.target.value))}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field
          label="Base fee (¢)"
          hint="Flat add-on on every quote"
          value={card.base_fee_cents}
          onChange={(n) => setField("base_fee_cents", n)}
        />
        <Field
          label="Per minute (¢)"
          hint="× estimated trip duration"
          value={card.per_minute_cents}
          onChange={(n) => setField("per_minute_cents", n)}
        />
        <Field
          label="Wait / minute (¢)"
          hint="× wait_minutes on the job"
          value={card.wait_cents_per_minute}
          onChange={(n) => setField("wait_cents_per_minute", n)}
        />
        <Field
          label="Extra stop (¢)"
          value={card.extra_stop_cents}
          onChange={(n) => setField("extra_stop_cents", n)}
        />
        <Field
          label="Liftgate (¢)"
          value={card.liftgate_cents}
          onChange={(n) => setField("liftgate_cents", n)}
        />
        <Field
          label="Rush surcharge (¢)"
          value={card.rush_surcharge_cents}
          onChange={(n) => setField("rush_surcharge_cents", n)}
        />
        <Field
          label="Scheduled surcharge (¢)"
          value={card.scheduled_surcharge_cents}
          onChange={(n) => setField("scheduled_surcharge_cents", n)}
        />
        <Field
          label="Weight threshold (kg)"
          value={card.weight_threshold_kg}
          onChange={(n) => setField("weight_threshold_kg", n)}
          step="0.1"
        />
        <Field
          label="Weight ¢ / kg over threshold"
          value={card.weight_cents_per_kg}
          onChange={(n) => setField("weight_cents_per_kg", n)}
        />
        <Field
          label="Declared value threshold (¢)"
          value={card.declared_value_threshold_cents}
          onChange={(n) => setField("declared_value_threshold_cents", n)}
        />
        <Field
          label="Declared value rate"
          hint="e.g. 0.01 = 1% of declared value"
          value={card.declared_value_rate}
          onChange={(n) => setField("declared_value_rate", n)}
          step="0.001"
        />
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field
          label="Weekend multiplier"
          hint="1.0 = off; 1.25 = +25%"
          value={card.weekend_multiplier}
          onChange={(n) => setField("weekend_multiplier", n)}
          step="0.01"
        />
        <Field
          label="Holiday multiplier"
          value={card.holiday_multiplier}
          onChange={(n) => setField("holiday_multiplier", n)}
          step="0.01"
        />
        <Field
          label="Night multiplier"
          value={card.night_multiplier}
          onChange={(n) => setField("night_multiplier", n)}
          step="0.01"
        />
        <Field
          label="Night start hour (0–23)"
          value={card.night_start_hour}
          onChange={(n) => setField("night_start_hour", n)}
        />
        <Field
          label="Night end hour (0–23)"
          value={card.night_end_hour}
          onChange={(n) => setField("night_end_hour", n)}
        />
        <label className="block text-sm sm:col-span-2 lg:col-span-3">
          <span className="font-medium text-primary">Holidays (MM-DD, comma-separated)</span>
          <input
            type="text"
            value={(card.holidays || []).join(", ")}
            onChange={(e) =>
              setField(
                "holidays",
                e.target.value
                  .split(",")
                  .map((s) => s.trim())
                  .filter(Boolean)
              )
            }
            className="mt-1 w-full rounded-xl border border-primary/10 px-3 py-2"
            placeholder="01-01, 07-01, 12-25"
          />
        </label>
      </section>

      <section className="space-y-4">
        <div>
          <h4 className="text-sm font-bold uppercase tracking-wide text-muted">Driver payout</h4>
          <p className="mt-1 text-xs text-muted">
            Credited to the driver wallet when a dropoff is completed. Flat mode uses the
            per-delivery fee; percent mode uses driver share % of the order total (after tax).
          </p>
        </div>
        <label className="block text-sm max-w-xs">
          <span className="font-medium text-primary">Payout mode</span>
          <select
            value={card.driver_payout_mode ?? "flat"}
            onChange={(e) =>
              setField("driver_payout_mode", e.target.value === "percent" ? "percent" : "flat")
            }
            className="mt-1 w-full rounded-xl border border-primary/10 px-3 py-2"
          >
            <option value="flat">Flat per delivery</option>
            <option value="percent">% of order total</option>
          </select>
        </label>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Field
            label="Flat per delivery (¢)"
            hint="Used when mode = flat (default $8.50 = 850¢)"
            value={card.driver_flat_per_delivery_cents}
            onChange={(n) => setField("driver_flat_per_delivery_cents", n)}
          />
          <Field
            label="Minimum payout (¢)"
            hint="Floor after flat or percent calc"
            value={card.driver_minimum_payout_cents}
            onChange={(n) => setField("driver_minimum_payout_cents", n)}
          />
          <Field
            label="Driver share %"
            hint="Used when mode = percent; also stored on quote metadata"
            value={card.driver_share_pct}
            onChange={(n) => setField("driver_share_pct", n)}
            step="0.1"
          />
          <Field
            label="PorterChain / platform share %"
            hint="Reporting / margin; should typically sum toward 100 with driver share"
            value={card.platform_share_pct}
            onChange={(n) => setField("platform_share_pct", n)}
            step="0.1"
          />
        </div>
      </section>
    </div>
  );
}
