"use client";

import { Button, Input } from "@/components/crm/primitives";
import type { MerchantGtaRate, MerchantGtaVehicleRates } from "@/lib/merchants";
import { DEFAULT_DOWNTOWN_FEE_CAD } from "@porterchain/types";

const DEFAULT_ROW: MerchantGtaVehicleRates = {
  base_price: 65,
  extra_km_rate: 2,
  extra_pick_fee: 20,
  extra_drop_fee: 15,
};

function num(v: string, fallback: number): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

export default function MerchantGtaMatrixFields({
  value,
  platform,
  vehicleIds,
  labels,
  onChange,
}: {
  value: MerchantGtaRate | null | undefined;
  platform: MerchantGtaRate | null | undefined;
  vehicleIds: string[];
  labels: Record<string, string>;
  onChange: (next: MerchantGtaRate | null) => void;
}) {
  const base = value ?? platform ?? {};
  const vehicles = { ...(platform?.vehicles || {}), ...(base.vehicles || {}) };
  const ids = vehicleIds.length ? vehicleIds : Object.keys(vehicles);

  function ensure(): MerchantGtaRate {
    return {
      base_km_limit: base.base_km_limit ?? platform?.base_km_limit ?? 20,
      downtown_fee_cad:
        base.downtown_fee_cad ?? platform?.downtown_fee_cad ?? DEFAULT_DOWNTOWN_FEE_CAD,
      upper_zone_fee_cad: base.upper_zone_fee_cad ?? platform?.upper_zone_fee_cad ?? 15,
      vehicles: { ...vehicles },
    };
  }

  function patchMeta(next: Partial<MerchantGtaRate>) {
    onChange({ ...ensure(), ...next });
  }

  function patchVehicle(id: string, next: Partial<MerchantGtaVehicleRates>) {
    const current = ensure();
    const row = { ...(current.vehicles?.[id] || platform?.vehicles?.[id] || DEFAULT_ROW), ...next };
    onChange({
      ...current,
      vehicles: { ...(current.vehicles || {}), [id]: row },
    });
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-primary">Distance matrix for this merchant</h3>
          <p className="mt-0.5 text-xs text-muted">
            Overrides the platform GTA card for Distance quotes only. Leave unset to use Settings →
            Pricing. Reset clears the overlay.
          </p>
        </div>
        <Button variant="outline" onClick={() => onChange(null)}>
          Use platform rates
        </Button>
      </div>

      {!value && (
        <p className="rounded-xl bg-gray-bg px-3 py-2 text-sm text-muted">
          Using platform GTA rates. Edit a field below to create a merchant-specific overlay.
        </p>
      )}

      <div className="grid gap-2 sm:grid-cols-3">
        <label className="text-xs font-medium text-primary/70">
          Base km included
          <Input
            className="mt-1"
            type="number"
            value={base.base_km_limit ?? 20}
            onChange={(e) => patchMeta({ base_km_limit: num(e.target.value, 20) })}
          />
        </label>
        <label className="text-xs font-medium text-primary/70">
          Downtown fee (CAD)
          <Input
            className="mt-1"
            type="number"
            value={base.downtown_fee_cad ?? DEFAULT_DOWNTOWN_FEE_CAD}
            onChange={(e) => patchMeta({ downtown_fee_cad: num(e.target.value, 0) })}
          />
        </label>
        <label className="text-xs font-medium text-primary/70">
          Upper zone fee (CAD)
          <Input
            className="mt-1"
            type="number"
            value={base.upper_zone_fee_cad ?? 15}
            onChange={(e) => patchMeta({ upper_zone_fee_cad: num(e.target.value, 0) })}
          />
        </label>
      </div>

      <div className="overflow-x-auto rounded-xl border border-primary/10">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-gray-bg text-xs text-muted">
            <tr>
              <th className="px-3 py-2 font-medium">Vehicle</th>
              <th className="px-3 py-2 font-medium">Base (CAD)</th>
              <th className="px-3 py-2 font-medium">Extra km</th>
              <th className="px-3 py-2 font-medium">Extra pick</th>
              <th className="px-3 py-2 font-medium">Extra drop</th>
            </tr>
          </thead>
          <tbody>
            {ids.map((id) => {
              const row = vehicles[id] || DEFAULT_ROW;
              return (
                <tr key={id} className="border-t border-primary/5">
                  <td className="px-3 py-2 font-medium text-primary">
                    {labels[id] || id.replace(/_/g, " ")}
                  </td>
                  {(
                    [
                      ["base_price", row.base_price],
                      ["extra_km_rate", row.extra_km_rate],
                      ["extra_pick_fee", row.extra_pick_fee],
                      ["extra_drop_fee", row.extra_drop_fee],
                    ] as const
                  ).map(([key, val]) => (
                    <td key={key} className="px-3 py-2">
                      <Input
                        type="number"
                        step="0.01"
                        value={val}
                        onChange={(e) => patchVehicle(id, { [key]: num(e.target.value, 0) })}
                      />
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
