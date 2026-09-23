"use client";

import type { BookingPreset, ParcelDraft } from "./parcelModel";

const RING =
  "w-full rounded-xl border border-primary/10 px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/40";

export default function ParcelEditor({
  parcels,
  presets,
  onChange,
}: {
  parcels: ParcelDraft[];
  presets: BookingPreset[];
  onChange: (next: ParcelDraft[]) => void;
}) {
  function patch(index: number, partial: Partial<ParcelDraft>) {
    onChange(parcels.map((row, i) => (i === index ? { ...row, ...partial } : row)));
  }

  return (
    <div className="space-y-3">
      {parcels.map((parcel, index) => {
        const preset = presets.find((item) => item.id === parcel.preset_id);
        const manual = Boolean(preset?.manual) || parcel.preset_id === "other";
        return (
          <div key={index} className="rounded-2xl border border-primary/10 p-3">
            <div className="grid gap-3 sm:grid-cols-3">
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-primary">Size</span>
                <select
                  className={RING}
                  value={parcel.preset_id}
                  onChange={(e) => patch(index, { preset_id: e.target.value })}
                >
                  {presets.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-primary">How many</span>
                <input
                  type="number"
                  min={1}
                  max={50}
                  className={RING}
                  value={parcel.quantity}
                  onChange={(e) =>
                    patch(index, { quantity: Math.max(1, Number(e.target.value) || 1) })
                  }
                />
              </label>
              <div className="flex items-end gap-2">
                <button
                  type="button"
                  className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
                  onClick={() => onChange([...parcels, { ...parcel, instructions: "" }])}
                >
                  Copy
                </button>
                {parcels.length > 1 && (
                  <button
                    type="button"
                    className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
                    onClick={() => onChange(parcels.filter((_, i) => i !== index))}
                  >
                    Remove
                  </button>
                )}
              </div>
            </div>
            {manual && (
              <div className="mt-3 grid gap-3 sm:grid-cols-4">
                {(
                  [
                    ["length_in", "Length (in)"],
                    ["width_in", "Width (in)"],
                    ["height_in", "Height (in)"],
                    ["weight_lb", "Weight (lb)"],
                  ] as const
                ).map(([key, label]) => (
                  <label key={key} className="block text-sm">
                    <span className="mb-1 block font-medium text-primary">{label}</span>
                    <input
                      type="number"
                      min={0}
                      className={RING}
                      value={parcel[key]}
                      onChange={(e) => patch(index, { [key]: e.target.value })}
                    />
                  </label>
                ))}
              </div>
            )}
            <label className="mt-3 block text-sm">
              <span className="mb-1 block font-medium text-primary">Note for this parcel</span>
              <input
                className={RING}
                value={parcel.instructions}
                onChange={(e) => patch(index, { instructions: e.target.value })}
                placeholder="Fragile, leave at side door"
              />
            </label>
          </div>
        );
      })}
      <button
        type="button"
        className="rounded-xl border border-primary/10 px-3 py-2 text-sm font-medium"
        onClick={() =>
          onChange([
            ...parcels,
            {
              preset_id: presets[0]?.id ?? "small",
              quantity: 1,
              instructions: "",
              length_in: "",
              width_in: "",
              height_in: "",
              weight_lb: "",
            },
          ])
        }
      >
        Add parcel
      </button>
    </div>
  );
}
