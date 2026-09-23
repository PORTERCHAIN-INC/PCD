"use client";

export const WEIGHT_OPTIONS = [
  { label: "1 kg", value: "1" },
  { label: "5 kg", value: "5" },
  { label: "10 kg", value: "10" },
  { label: "25 kg", value: "25" },
];

export const DIMENSION_OPTIONS = [
  { label: "Envelope", value: "Envelope" },
  { label: "30 × 20 × 10 cm", value: "30 x 20 x 10 cm" },
  { label: "40 × 30 × 20 cm", value: "40 x 30 x 20 cm" },
  { label: "60 × 40 × 40 cm", value: "60 x 40 x 40 cm" },
];

export const VALUE_OPTIONS = [
  { label: "$100", value: "100" },
  { label: "$500", value: "500" },
  { label: "$1,000", value: "1000" },
  { label: "$5,000", value: "5000" },
];

export const INSTRUCTION_OPTIONS = [
  { label: "Call on arrival", value: "Call on arrival" },
  { label: "Leave at the door", value: "Leave at the door" },
  { label: "Reception", value: "Leave with reception or the front desk" },
  { label: "Buzz code", value: "Buzz code is on the door" },
];

export function FieldSuggestions({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (next: string) => void;
  options: { label: string; value: string }[];
}) {
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {options.map((item) => {
        const on = value === item.value;
        return (
          <button
            key={item.value}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(on ? "" : item.value)}
            className={
              on
                ? "rounded-full bg-secondary px-3 py-1.5 text-xs font-semibold text-white"
                : "rounded-full border border-primary/10 bg-white px-3 py-1.5 text-xs font-semibold text-primary"
            }
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}

/** Display a Canadian number as +1 xxx-xxx-xxxx while the customer types. */
export function parseWeightKg(raw: string): number | undefined {
  const cleaned = raw.trim();
  if (!cleaned) return undefined;
  const n = Number(cleaned);
  if (!Number.isFinite(n) || n < 0) return undefined;
  return n;
}

export function parseDeclaredCents(raw: string): number | undefined {
  const cleaned = raw.replace(/[$,\s]/g, "");
  if (!cleaned) return undefined;
  const n = Number(cleaned);
  if (!Number.isFinite(n) || n < 0) return undefined;
  return Math.round(n * 100);
}

export function formatCanadianPhone(input: string): string {
  let digits = input.replace(/\D/g, "");
  if (digits.startsWith("1")) digits = digits.slice(1);
  digits = digits.slice(0, 10);
  if (!digits) return "";
  const area = digits.slice(0, 3);
  const prefix = digits.slice(3, 6);
  const line = digits.slice(6, 10);
  if (digits.length <= 3) return `+1 ${area}`;
  if (digits.length <= 6) return `+1 ${area}-${prefix}`;
  return `+1 ${area}-${prefix}-${line}`;
}
