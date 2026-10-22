"use client";

import {
  DELIVERY_FLAGS,
  DELIVERY_TEXT_LIMITS,
  DROP_METHODS,
  type DeliveryOptions,
} from "@porterchain/types/delivery-options";

type Props = {
  value: DeliveryOptions;
  onChange: (next: DeliveryOptions) => void;
  /** Prefix for input ids (several forms can sit on one page). */
  idPrefix?: string;
  /** Hide the free-text note when the surface already has its own instructions box. */
  hideNote?: boolean;
  className?: string;
};

const box = "mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm";

/** Shared "Delivery options" block — merchant portal, customer web, admin. */
export function DeliveryOptionsFields({
  value,
  onChange,
  idPrefix = "dlv",
  hideNote = false,
  className,
}: Props) {
  const set = (patch: Partial<DeliveryOptions>) => onChange({ ...value, ...patch });
  return (
    <fieldset className={className} data-testid="delivery-options">
      <legend className="text-sm font-medium text-primary">Delivery options</legend>
      <div className="mt-2 flex flex-wrap gap-2" role="radiogroup" aria-label="How to hand over">
        {DROP_METHODS.map((m) => {
          const on = value.drop_method === m.id;
          return (
            <button
              key={m.id}
              type="button"
              role="radio"
              aria-checked={on}
              title={m.hint}
              data-testid={`${idPrefix}-drop-${m.id}`}
              onClick={() => set({ drop_method: on ? null : m.id })}
              className={`rounded-full border px-3 py-1.5 text-xs font-medium ${
                on ? "border-primary bg-primary text-white" : "border-primary/20 text-primary"
              }`}
            >
              {m.label}
            </button>
          );
        })}
      </div>
      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2">
        {DELIVERY_FLAGS.map((f) => (
          <label key={f.id} className="inline-flex items-center gap-2 text-sm text-primary">
            <input
              type="checkbox"
              id={`${idPrefix}-${f.id}`}
              checked={Boolean(value[f.id])}
              onChange={(e) => set({ [f.id]: e.target.checked })}
            />
            {f.label}
          </label>
        ))}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <label className="text-sm text-primary" htmlFor={`${idPrefix}-unit`}>
          Apartment / unit
          <input
            id={`${idPrefix}-unit`}
            className={box}
            maxLength={DELIVERY_TEXT_LIMITS.unit}
            value={value.unit ?? ""}
            onChange={(e) => set({ unit: e.target.value })}
          />
        </label>
        <label className="text-sm text-primary" htmlFor={`${idPrefix}-buzzer`}>
          Buzzer code
          <input
            id={`${idPrefix}-buzzer`}
            className={box}
            maxLength={DELIVERY_TEXT_LIMITS.buzzer}
            value={value.buzzer ?? ""}
            onChange={(e) => set({ buzzer: e.target.value })}
          />
        </label>
      </div>
      {hideNote ? null : (
        <label className="mt-3 block text-sm text-primary" htmlFor={`${idPrefix}-note`}>
          Note for the driver
          <textarea
            id={`${idPrefix}-note`}
            className={box}
            rows={2}
            maxLength={DELIVERY_TEXT_LIMITS.note}
            value={value.note ?? ""}
            onChange={(e) => set({ note: e.target.value })}
          />
        </label>
      )}
    </fieldset>
  );
}
