"use client";

import { Plus, Trash2 } from "lucide-react";
import type { ReactNode } from "react";
import { Button, Input, Select } from "@/components/crm/primitives";
import {
  BLANK_SIZE_TIER,
  DEFAULT_MERCHANT_SCHEDULE,
  type DimensionUnit,
  type MerchantPricing,
  type MerchantSchedule,
  type MerchantSizeTier,
  type PricingModel,
  type WeightUnit,
} from "@/lib/merchants";

const DIMENSION_UNITS: DimensionUnit[] = ["cm", "in", "ft"];
const WEIGHT_UNITS: WeightUnit[] = ["kg", "lb"];

const MODELS: { id: PricingModel; label: string; blurb: string }[] = [
  {
    id: "distance",
    label: "Distance",
    blurb: "Price from the GTA vehicle matrix — base fare, extra kilometres, extra stops.",
  },
  {
    id: "fsa",
    label: "FSA flat rates",
    blurb:
      "Price from the postal-code table for this merchant. Destinations without a rate use distance — or refuse, when the schedule says so.",
  },
];

function numOrNull(raw: string): number | null {
  if (raw.trim() === "") return null;
  const n = Number(raw);
  return Number.isFinite(n) && n >= 0 ? n : null;
}

function LimitInput({
  value,
  onChange,
  placeholder,
}: {
  value: number | null;
  onChange: (v: number | null) => void;
  placeholder: string;
}) {
  return (
    <Input
      type="number"
      min="0"
      step="0.1"
      value={value ?? ""}
      placeholder={placeholder}
      onChange={(e) => onChange(numOrNull(e.target.value))}
    />
  );
}

export default function MerchantPricingFields({
  value,
  onChange,
  fsaHint,
}: {
  value: MerchantPricing;
  onChange: (next: MerchantPricing) => void;
  fsaHint?: ReactNode;
}) {
  function patch(next: Partial<MerchantPricing>) {
    onChange({ ...value, ...next });
  }

  function patchTier(index: number, next: Partial<MerchantSizeTier>) {
    onChange({
      ...value,
      size_tiers: value.size_tiers.map((t, i) => (i === index ? { ...t, ...next } : t)),
    });
  }

  return (
    <div className="space-y-6">
      <section>
        <h3 className="text-sm font-semibold text-primary">How this merchant is priced</h3>
        <p className="mb-3 mt-0.5 text-xs text-muted">
          Distance uses kilometres. FSA uses the destination postal code. Automatic tries FSA first.
        </p>
        <div className="space-y-2">
          {MODELS.map((m) => (
            <label
              key={m.id}
              className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition-colors ${
                value.pricing_model === m.id
                  ? "border-secondary bg-secondary/5"
                  : "border-primary/10 hover:bg-gray-bg/60"
              }`}
            >
              <input
                type="radio"
                className="mt-1"
                name="merchant-pricing-model"
                checked={value.pricing_model === m.id}
                onChange={() => patch({ pricing_model: m.id })}
              />
              <span>
                <span className="text-sm font-semibold text-primary">{m.label}</span>
                <span className="block text-xs text-muted">{m.blurb}</span>
              </span>
            </label>
          ))}
        </div>
        {value.pricing_model === "fsa" && fsaHint}
      </section>

      <section>
        <h3 className="text-sm font-semibold text-primary">Location surcharges</h3>
        <p className="mb-3 mt-0.5 text-xs text-muted">
          Uncheck to waive a fee for this merchant. The quote still records that the stop was
          downtown or upper-zone, so a waiver is visible rather than looking like a miss.
        </p>
        <div className="space-y-2">
          {(
            [
              ["downtown", "Downtown Toronto surcharge"],
              ["upper_zone", "Markham / North York surcharge"],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="flex items-center gap-2 text-sm text-primary">
              <input
                type="checkbox"
                checked={value.surcharges[key]}
                onChange={(e) =>
                  patch({ surcharges: { ...value.surcharges, [key]: e.target.checked } })
                }
              />
              Charge the {label.toLowerCase()}
            </label>
          ))}
        </div>
      </section>

      <ScheduleFields
        value={value.schedule ?? DEFAULT_MERCHANT_SCHEDULE}
        onChange={(schedule) => patch({ schedule })}
      />

      <section>
        <div className="mb-3 flex items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-primary">Size and weight surcharges</h3>
            <p className="mt-0.5 text-xs text-muted">
              Extra charge on top of the distance or FSA price. Rows are checked top to bottom and
              the first one the shipment fits wins — put the smallest first. Leave a limit blank for
              “any”. Units are per row: centimetres, inches or feet; kilograms or pounds.
            </p>
          </div>
          <Button
            variant="outline"
            onClick={() => patch({ size_tiers: [...value.size_tiers, { ...BLANK_SIZE_TIER }] })}
          >
            <Plus className="h-4 w-4" /> Add row
          </Button>
        </div>

        {value.size_tiers.length === 0 ? (
          <p className="rounded-xl bg-gray-bg px-3 py-6 text-center text-sm text-muted">
            No size rules. This merchant uses the platform rate-card thresholds.
          </p>
        ) : (
          <div className="space-y-3">
            {value.size_tiers.map((tier, i) => (
              <div key={i} className="rounded-xl border border-primary/10 p-3">
                <div className="mb-2 flex items-center gap-2">
                  <span className="rounded-md bg-gray-bg px-2 py-0.5 text-xs font-medium text-muted">
                    {i + 1}
                  </span>
                  <Input
                    value={tier.label}
                    placeholder="Row name — e.g. Standard pallet"
                    onChange={(e) => patchTier(i, { label: e.target.value })}
                  />
                  <button
                    type="button"
                    title="Remove row"
                    onClick={() =>
                      patch({ size_tiers: value.size_tiers.filter((_, x) => x !== i) })
                    }
                    className="rounded-lg p-2 text-muted hover:bg-red-50 hover:text-red-700"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>

                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                  <div>
                    <span className="text-xs font-medium text-primary/70">
                      Max length × width × height
                    </span>
                    <div className="mt-1 flex gap-1">
                      <LimitInput
                        value={tier.max_length}
                        placeholder="L"
                        onChange={(v) => patchTier(i, { max_length: v })}
                      />
                      <LimitInput
                        value={tier.max_width}
                        placeholder="W"
                        onChange={(v) => patchTier(i, { max_width: v })}
                      />
                      <LimitInput
                        value={tier.max_height}
                        placeholder="H"
                        onChange={(v) => patchTier(i, { max_height: v })}
                      />
                    </div>
                  </div>
                  <div>
                    <span className="text-xs font-medium text-primary/70">Dimension units</span>
                    <Select
                      className="mt-1"
                      value={tier.dimension_unit}
                      onChange={(e) =>
                        patchTier(i, { dimension_unit: e.target.value as DimensionUnit })
                      }
                    >
                      {DIMENSION_UNITS.map((u) => (
                        <option key={u} value={u}>
                          {u === "cm"
                            ? "centimetres (cm)"
                            : u === "in"
                              ? "inches (in)"
                              : "feet (ft)"}
                        </option>
                      ))}
                    </Select>
                  </div>
                  <div>
                    <span className="text-xs font-medium text-primary/70">Max weight</span>
                    <div className="mt-1 flex gap-1">
                      <LimitInput
                        value={tier.max_weight}
                        placeholder="Any"
                        onChange={(v) => patchTier(i, { max_weight: v })}
                      />
                      <Select
                        value={tier.weight_unit}
                        className="max-w-[110px]"
                        onChange={(e) =>
                          patchTier(i, { weight_unit: e.target.value as WeightUnit })
                        }
                      >
                        {WEIGHT_UNITS.map((u) => (
                          <option key={u} value={u}>
                            {u === "kg" ? "kg" : "lb"}
                          </option>
                        ))}
                      </Select>
                    </div>
                  </div>
                  <div>
                    <span className="text-xs font-medium text-primary/70">Surcharge (CAD)</span>
                    <Input
                      className="mt-1"
                      type="number"
                      min="0"
                      step="0.01"
                      value={(tier.surcharge_cents / 100).toFixed(2)}
                      onChange={(e) =>
                        patchTier(i, {
                          surcharge_cents: Math.max(
                            0,
                            Math.round(Number(e.target.value || 0) * 100)
                          ),
                        })
                      }
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function ScheduleFields({
  value,
  onChange,
}: {
  value: MerchantSchedule;
  onChange: (next: MerchantSchedule) => void;
}) {
  function patch(next: Partial<MerchantSchedule>) {
    onChange({ ...value, ...next });
  }

  const fuelBlank =
    value.fuel_surcharge_percent === null || value.fuel_surcharge_percent === undefined;
  const minsText = Object.entries(value.route_minimums_cents || {})
    .map(([k, v]) => `${k}=${(v / 100).toFixed(2)}`)
    .join(", ");

  return (
    <section>
      <h3 className="text-sm font-semibold text-primary">Commercial schedule</h3>
      <p className="mb-3 mt-0.5 text-xs text-muted">
        Fuel override, FSA miss behaviour, origin pickup, route minimums by FSA tier, compact
        banding, and size-match mode. Leave fuel blank to use platform Settings → Pricing.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <span className="text-xs font-medium text-primary/70">
            Fuel surcharge % (blank = platform)
          </span>
          <Input
            className="mt-1"
            type="number"
            min="0"
            step="0.1"
            value={fuelBlank ? "" : String(value.fuel_surcharge_percent)}
            placeholder="platform"
            onChange={(e) => {
              const raw = e.target.value.trim();
              patch({
                fuel_surcharge_percent: raw === "" ? null : Math.max(0, Number(raw) || 0),
              });
            }}
          />
        </div>
        <div>
          <span className="text-xs font-medium text-primary/70">
            When destination has no FSA rate
          </span>
          <Select
            className="mt-1"
            value={value.fsa_miss}
            onChange={(e) => patch({ fsa_miss: e.target.value as MerchantSchedule["fsa_miss"] })}
          >
            <option value="fallback_distance">Fall back to distance (default)</option>
            <option value="refuse">Refuse quote (no rate)</option>
          </Select>
        </div>
        <div>
          <span className="text-xs font-medium text-primary/70">Origin pickup (CAD)</span>
          <Input
            className="mt-1"
            type="number"
            min="0"
            step="0.01"
            value={(value.origin_pickup_cents / 100).toFixed(2)}
            onChange={(e) =>
              patch({
                origin_pickup_cents: Math.max(0, Math.round(Number(e.target.value || 0) * 100)),
              })
            }
          />
        </div>
        <div>
          <span className="text-xs font-medium text-primary/70">Pickup vehicle classes</span>
          <Input
            className="mt-1"
            value={(value.origin_pickup_vehicle_classes || []).join(", ")}
            placeholder="cargo_van"
            onChange={(e) =>
              patch({
                origin_pickup_vehicle_classes: e.target.value
                  .split(",")
                  .map((s) => s.trim())
                  .filter(Boolean),
              })
            }
          />
        </div>
        <div className="sm:col-span-2">
          <span className="text-xs font-medium text-primary/70">
            Route minimums by FSA tier (e.g. T1=120, T2=200)
          </span>
          <Input
            className="mt-1"
            value={minsText}
            placeholder="T1=120, T2=200, T3=250"
            onChange={(e) => {
              const next: Record<string, number> = {};
              for (const part of e.target.value.split(",")) {
                const [k, v] = part.split("=").map((s) => s.trim());
                if (!k) continue;
                const dollars = Number(v);
                if (!Number.isFinite(dollars) || dollars < 0) continue;
                next[k] = Math.round(dollars * 100);
              }
              patch({ route_minimums_cents: next });
            }}
          />
        </div>
        <div>
          <span className="text-xs font-medium text-primary/70">Size match</span>
          <Select
            className="mt-1"
            value={value.size_match}
            onChange={(e) =>
              patch({ size_match: e.target.value as MerchantSchedule["size_match"] })
            }
          >
            <option value="all">All limits (AND)</option>
            <option value="any">Weight or footprint (OR)</option>
          </Select>
        </div>
        <div className="flex items-end">
          <label className="flex items-center gap-2 text-sm text-primary">
            <input
              type="checkbox"
              checked={value.compact.enabled}
              onChange={(e) => patch({ compact: { ...value.compact, enabled: e.target.checked } })}
            />
            Enable compact stop banding
          </label>
        </div>
        {value.compact.enabled ? (
          <>
            <div>
              <span className="text-xs font-medium text-primary/70">
                Compact route minimum (CAD)
              </span>
              <Input
                className="mt-1"
                type="number"
                min="0"
                step="0.01"
                value={(value.compact.route_minimum_cents / 100).toFixed(2)}
                onChange={(e) =>
                  patch({
                    compact: {
                      ...value.compact,
                      route_minimum_cents: Math.max(
                        0,
                        Math.round(Number(e.target.value || 0) * 100)
                      ),
                    },
                  })
                }
              />
            </div>
            <div>
              <span className="text-xs font-medium text-primary/70">Parcels per stop</span>
              <Input
                className="mt-1"
                type="number"
                min="1"
                value={value.compact.parcels_per_stop}
                onChange={(e) =>
                  patch({
                    compact: {
                      ...value.compact,
                      parcels_per_stop: Math.max(1, Math.round(Number(e.target.value || 1))),
                    },
                  })
                }
              />
            </div>
          </>
        ) : null}
      </div>
    </section>
  );
}
