"use client";

import { useMemo, useState } from "react";
import { Button, Field, Input } from "@/components/crm/primitives";
import { SettingsCard } from "../ui/SettingsPrimitives";

import { CAPACITY_CLASS_IDS, DEFAULT_DOWNTOWN_FEE_CAD, vehicleLabel } from "@porterchain/types";

type Rates = {
  base_price: number;
  extra_km_rate: number;
  extra_pick_fee: number;
  extra_drop_fee: number;
};

type Preset = {
  id: string;
  label: string;
  length_in: number | null;
  width_in: number | null;
  height_in: number | null;
  weight_lb: number | null;
  manual: boolean;
};

type CustomerCard = {
  base_km_limit: number;
  downtown_fee_cad: number;
  upper_zone_fee_cad: number;
  weight_threshold_kg: number;
  weight_cents_per_kg: number;
  volume_threshold_cm3: number;
  cents_per_10k_cm3: number;
  declared_value_threshold_cents: number;
  declared_value_rate: number;
  vehicles: Record<string, Rates>;
  parcel_presets: Preset[];
};

const VEHICLES = CAPACITY_CLASS_IDS;

function num(value: unknown, fallback: number): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function normalize(raw: unknown): CustomerCard {
  const src = typeof raw === "object" && raw !== null ? (raw as Record<string, unknown>) : {};
  const vehiclesRaw =
    typeof src.vehicles === "object" && src.vehicles !== null
      ? (src.vehicles as Record<string, Record<string, unknown>>)
      : {};
  const vehicles: Record<string, Rates> = {};
  for (const id of VEHICLES) {
    if (!vehiclesRaw[id]) continue;
    const row = vehiclesRaw[id];
    vehicles[id] = {
      base_price: num(row.base_price, 0),
      extra_km_rate: num(row.extra_km_rate, 0),
      extra_pick_fee: num(row.extra_pick_fee, 0),
      extra_drop_fee: num(row.extra_drop_fee, 0),
    };
  }
  const presetsRaw = Array.isArray(src.parcel_presets) ? src.parcel_presets : [];
  const parcel_presets: Preset[] = presetsRaw
    .filter((row): row is Record<string, unknown> => typeof row === "object" && row !== null)
    .map((row) => ({
      id: String(row.id ?? ""),
      label: String(row.label ?? row.id ?? ""),
      length_in: row.length_in == null || row.length_in === "" ? null : num(row.length_in, 0),
      width_in: row.width_in == null || row.width_in === "" ? null : num(row.width_in, 0),
      height_in: row.height_in == null || row.height_in === "" ? null : num(row.height_in, 0),
      weight_lb: row.weight_lb == null || row.weight_lb === "" ? null : num(row.weight_lb, 0),
      manual: Boolean(row.manual) || row.id === "other",
    }))
    .filter((row) => row.id);
  return {
    base_km_limit: num(src.base_km_limit, 20),
    downtown_fee_cad: num(src.downtown_fee_cad, DEFAULT_DOWNTOWN_FEE_CAD),
    upper_zone_fee_cad: num(src.upper_zone_fee_cad, 15),
    weight_threshold_kg: num(src.weight_threshold_kg, 50),
    weight_cents_per_kg: num(src.weight_cents_per_kg, 0),
    volume_threshold_cm3: num(src.volume_threshold_cm3, 100000),
    cents_per_10k_cm3: num(src.cents_per_10k_cm3, 0),
    declared_value_threshold_cents: num(src.declared_value_threshold_cents, 0),
    declared_value_rate: num(src.declared_value_rate, 0),
    vehicles,
    parcel_presets,
  };
}

function blankRates(): Rates {
  return { base_price: 45, extra_km_rate: 1.25, extra_pick_fee: 20, extra_drop_fee: 15 };
}

export default function CustomerPricingPanel({
  data,
  saving,
  onSave,
}: {
  data: unknown;
  saving?: boolean;
  onSave: (value: CustomerCard, reason: string) => Promise<void>;
}) {
  const initial = useMemo(() => normalize(data), [data]);
  const [card, setCard] = useState(initial);
  const [reason, setReason] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const [addId, setAddId] = useState<string>("sedan_suv");

  function setVehicle(id: string, patch: Partial<Rates>) {
    setCard({
      ...card,
      vehicles: { ...card.vehicles, [id]: { ...card.vehicles[id], ...patch } },
    });
  }

  function setPreset(index: number, patch: Partial<Preset>) {
    const parcel_presets = card.parcel_presets.map((row, i) =>
      i === index ? { ...row, ...patch } : row
    );
    setCard({ ...card, parcel_presets });
  }

  const sample = useMemo(() => {
    const sedan = card.vehicles.sedan_suv;
    if (!sedan) return "Add a Sedan / SUV rate to preview.";
    const km = 28;
    const extraKm = Math.max(0, km - card.base_km_limit);
    const base = Math.round(sedan.base_price * 100);
    const extra = Math.round(extraKm * sedan.extra_km_rate * 100);
    const drop = Math.round(sedan.extra_drop_fee * 100);
    const downtown = Math.round(card.downtown_fee_cad * 100);
    const weight = Math.round(
      Math.max(0, 30 - card.weight_threshold_kg) * card.weight_cents_per_kg
    );
    const total = base + extra + drop + downtown + weight;
    return `28 km, one extra drop, downtown, 30 kg: $${(total / 100).toFixed(2)} before tax. Included kilometres stay inside the base.`;
  }, [card]);

  async function save() {
    if (!reason.trim()) {
      setToast("A save reason is required.");
      return;
    }
    try {
      await onSave(
        { ...card, strict_vehicles: true } as CustomerCard & { strict_vehicles: boolean },
        reason.trim()
      );
      setToast("Saved. Customer quotes use this card only.");
      setReason("");
    } catch (err) {
      setToast(err instanceof Error ? err.message : "Save failed");
    }
  }

  const missing = VEHICLES.filter((id) => !card.vehicles[id]);

  return (
    <div className="space-y-6">
      <SettingsCard
        title="Customer distance"
        description="One price card for customer web and the phone app. Merchant FSA and the rate card are not used here."
      >
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Included km">
            <Input
              type="number"
              min={0}
              value={card.base_km_limit}
              onChange={(e) => setCard({ ...card, base_km_limit: num(e.target.value, 0) })}
            />
          </Field>
          <Field label="Downtown ($)">
            <Input
              type="number"
              min={0}
              step="0.01"
              value={card.downtown_fee_cad}
              onChange={(e) => setCard({ ...card, downtown_fee_cad: num(e.target.value, 0) })}
            />
          </Field>
          <Field label="Upper zone ($)">
            <Input
              type="number"
              min={0}
              step="0.01"
              value={card.upper_zone_fee_cad}
              onChange={(e) => setCard({ ...card, upper_zone_fee_cad: num(e.target.value, 0) })}
            />
          </Field>
          <Field label="Weight included (kg)">
            <Input
              type="number"
              min={0}
              value={card.weight_threshold_kg}
              onChange={(e) => setCard({ ...card, weight_threshold_kg: num(e.target.value, 0) })}
            />
          </Field>
          <Field label="Cents per extra kg">
            <Input
              type="number"
              min={0}
              value={card.weight_cents_per_kg}
              onChange={(e) => setCard({ ...card, weight_cents_per_kg: num(e.target.value, 0) })}
            />
          </Field>
          <Field label="Volume included (cm³)">
            <Input
              type="number"
              min={0}
              value={card.volume_threshold_cm3}
              onChange={(e) => setCard({ ...card, volume_threshold_cm3: num(e.target.value, 0) })}
            />
          </Field>
          <Field label="Cents per 10,000 cm³">
            <Input
              type="number"
              min={0}
              value={card.cents_per_10k_cm3}
              onChange={(e) => setCard({ ...card, cents_per_10k_cm3: num(e.target.value, 0) })}
            />
          </Field>
          <Field label="Declared value included (cents)">
            <Input
              type="number"
              min={0}
              value={card.declared_value_threshold_cents}
              onChange={(e) =>
                setCard({ ...card, declared_value_threshold_cents: num(e.target.value, 0) })
              }
            />
          </Field>
          <Field label="Declared value rate">
            <Input
              type="number"
              min={0}
              step="0.0001"
              value={card.declared_value_rate}
              onChange={(e) => setCard({ ...card, declared_value_rate: num(e.target.value, 0) })}
            />
          </Field>
        </div>
        <p className="mt-3 text-sm text-secondary">{sample}</p>
      </SettingsCard>

      <SettingsCard
        title="Vehicle rates"
        description="Delete hides that vehicle from customer quotes. It does not change merchant prices."
      >
        <div className="mb-3 flex flex-wrap items-end gap-2">
          <Field label="Add vehicle">
            <select
              className="rounded-lg border border-gray-line px-3 py-2"
              value={addId}
              onChange={(e) => setAddId(e.target.value)}
            >
              {missing.map((id) => (
                <option key={id} value={id}>
                  {vehicleLabel(id, id)}
                </option>
              ))}
            </select>
          </Field>
          <Button
            variant="outline"
            disabled={!missing.length}
            onClick={() =>
              setCard({ ...card, vehicles: { ...card.vehicles, [addId]: blankRates() } })
            }
          >
            Add
          </Button>
        </div>
        {!Object.keys(card.vehicles).length ? (
          <p className="text-sm text-muted">
            No customer vehicle rates yet. Add one to show that vehicle on booking.
          </p>
        ) : null}
        {["sedan_suv", "cargo_van", "pickup", "box_16", "box_20"].some(
          (id) => !card.vehicles[id]
        ) ? (
          <p className="text-sm text-amber-800">
            A retail vehicle has no customer rate, so booking will hide it until a rate is added.
          </p>
        ) : null}
        <div className="flex justify-end">
          <Button variant="outline" onClick={() => setCard(initial)}>
            Reset
          </Button>
        </div>
        <div className="space-y-4">
          {Object.entries(card.vehicles).map(([id, rates]) => (
            <div key={id} className="rounded-xl border border-gray-line p-3">
              <div className="mb-2 flex items-center justify-between">
                <p className="font-medium">{vehicleLabel(id, id)}</p>
                <Button
                  variant="outline"
                  onClick={() => {
                    if (!window.confirm(`Remove the ${vehicleLabel(id, id)} customer rate?`))
                      return;
                    const vehicles = { ...card.vehicles };
                    delete vehicles[id];
                    setCard({ ...card, vehicles });
                  }}
                >
                  Delete
                </Button>
              </div>
              <div className="grid gap-3 sm:grid-cols-4">
                {(
                  [
                    ["base_price", "Base $"],
                    ["extra_km_rate", "$ / km after included"],
                    ["extra_pick_fee", "Extra pickup $"],
                    ["extra_drop_fee", "Extra drop $"],
                  ] as const
                ).map(([key, label]) => (
                  <Field key={key} label={label}>
                    <Input
                      type="number"
                      min={0}
                      step="0.01"
                      value={rates[key]}
                      onChange={(e) => setVehicle(id, { [key]: num(e.target.value, 0) })}
                    />
                  </Field>
                ))}
              </div>
            </div>
          ))}
        </div>
      </SettingsCard>

      <SettingsCard
        title="Parcel presets"
        description="Inches and pounds. The server converts once. Other cannot be deleted."
      >
        <div className="space-y-3">
          {card.parcel_presets.map((preset, index) => (
            <div key={preset.id} className="grid gap-2 sm:grid-cols-6">
              <Field label="Name">
                <Input
                  value={preset.label}
                  onChange={(e) => setPreset(index, { label: e.target.value })}
                />
              </Field>
              <Field label="L (in)">
                <Input
                  type="number"
                  min={0}
                  disabled={preset.manual}
                  value={preset.length_in ?? ""}
                  onChange={(e) => setPreset(index, { length_in: num(e.target.value, 0) })}
                />
              </Field>
              <Field label="W (in)">
                <Input
                  type="number"
                  min={0}
                  disabled={preset.manual}
                  value={preset.width_in ?? ""}
                  onChange={(e) => setPreset(index, { width_in: num(e.target.value, 0) })}
                />
              </Field>
              <Field label="H (in)">
                <Input
                  type="number"
                  min={0}
                  disabled={preset.manual}
                  value={preset.height_in ?? ""}
                  onChange={(e) => setPreset(index, { height_in: num(e.target.value, 0) })}
                />
              </Field>
              <Field label="lb">
                <Input
                  type="number"
                  min={0}
                  disabled={preset.manual}
                  value={preset.weight_lb ?? ""}
                  onChange={(e) => setPreset(index, { weight_lb: num(e.target.value, 0) })}
                />
              </Field>
              <div className="flex items-end">
                {preset.id !== "other" && (
                  <Button
                    variant="outline"
                    onClick={() =>
                      setCard({
                        ...card,
                        parcel_presets: card.parcel_presets.filter((_, i) => i !== index),
                      })
                    }
                  >
                    Delete
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      </SettingsCard>

      <div className="flex flex-wrap items-end gap-2">
        <Field label="Reason">
          <Input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Why this price changed"
          />
        </Field>
        <Button variant="primary" disabled={saving} onClick={() => void save()}>
          {saving ? "Saving…" : "Save customer prices"}
        </Button>
      </div>
      {toast && <p className="text-sm text-secondary">{toast}</p>}
    </div>
  );
}
