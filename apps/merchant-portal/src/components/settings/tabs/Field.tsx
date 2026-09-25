"use client";

export function Field({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  return (
    <div>
      <label className="text-sm font-medium text-primary">{label}</label>
      <input
        disabled={disabled}
        className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm disabled:bg-gray-bg"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
