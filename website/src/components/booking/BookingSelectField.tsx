"use client";

import type { LucideIcon } from "lucide-react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export type BookingSelectOption = {
  value: string;
  label: string;
};

type BookingSelectFieldProps = {
  id: string;
  label: string;
  icon?: LucideIcon;
  value: string;
  options: BookingSelectOption[];
  onChange: (value: string) => void;
  compact?: boolean;
  className?: string;
};

export default function BookingSelectField({
  id,
  label,
  icon: Icon,
  value,
  options,
  onChange,
  compact = false,
  className,
}: BookingSelectFieldProps) {
  return (
    <div className={cn("min-w-0", className)}>
      <label htmlFor={id} className="type-caption font-bold text-muted mb-1 flex items-center gap-1.5">
        {Icon && <Icon className="w-3.5 h-3.5 shrink-0" />}
        {label}
      </label>
      <div className="relative">
        <select
          id={id}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={cn(
            "booking-select-field w-full appearance-none pr-9",
            compact && "booking-select-field-compact"
          )}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <ChevronDown
          className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
          aria-hidden
        />
      </div>
    </div>
  );
}
