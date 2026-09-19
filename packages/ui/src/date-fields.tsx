"use client";

import { format } from "date-fns";
import {
  DateTimePickerSeparate,
  type DateTimePickerSeparateProps,
} from "./datetime-picker-separate";
import { cn } from "./utils";

/** `yyyy-MM-dd`, the shape our filter and date-only API params use. */
export function toDateString(date: Date): string {
  return format(date, "yyyy-MM-dd");
}

/**
 * Parses `yyyy-MM-dd` as a local date. `new Date("2026-09-09")` is parsed as
 * UTC midnight, which renders as the previous day west of Greenwich.
 */
export function parseDateString(value: string | undefined | null): Date | undefined {
  const raw = value?.trim();
  if (!raw) return undefined;
  const [y, m, d] = raw.slice(0, 10).split("-").map(Number);
  if (!y || !m || !d) return undefined;
  const date = new Date(y, m - 1, d);
  return Number.isNaN(date.getTime()) ? undefined : date;
}

type SharedProps = Omit<
  DateTimePickerSeparateProps,
  "value" | "onChange" | "showTime" | "dateLabel" | "timeLabel"
>;

export type DateFieldProps = SharedProps & {
  /** `yyyy-MM-dd` */
  value: string;
  onChange: (value: string) => void;
  label?: string;
};

/** Date-only control. Use wherever a native `<input type="date">` would go. */
export function DateField({ value, onChange, label, ...props }: DateFieldProps) {
  return (
    <DateTimePickerSeparate
      {...props}
      showTime={false}
      dateLabel={label}
      value={parseDateString(value)}
      onChange={(date) => onChange(date ? toDateString(date) : "")}
    />
  );
}

export type DateTimeFieldProps = SharedProps & {
  /** `yyyy-MM-ddTHH:mm` — the same shape `<input type="datetime-local">` produces. */
  value: string;
  onChange: (value: string) => void;
  label?: string;
  timeLabel?: string;
};

/** Date + time control. Use wherever a native `datetime-local` would go. */
export function DateTimeField({
  value,
  onChange,
  label = "Date",
  timeLabel = "Time",
  ...props
}: DateTimeFieldProps) {
  return (
    <DateTimePickerSeparate
      {...props}
      dateLabel={label}
      timeLabel={timeLabel}
      value={parseLocalDateTime(value)}
      onChange={(date) => onChange(date ? format(date, "yyyy-MM-dd'T'HH:mm") : "")}
    />
  );
}

function parseLocalDateTime(value: string | undefined | null): Date | undefined {
  if (!value?.trim()) return undefined;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? undefined : date;
}

export type DateRangeFieldProps = SharedProps & {
  /** `yyyy-MM-dd` */
  from: string;
  /** `yyyy-MM-dd` */
  to: string;
  onFromChange: (value: string) => void;
  onToChange: (value: string) => void;
  fromLabel?: string;
  toLabel?: string;
  className?: string;
};

/** From/to pair that keeps each side from crossing the other. */
export function DateRangeField({
  from,
  to,
  onFromChange,
  onToChange,
  fromLabel = "From",
  toLabel = "To",
  className,
  ...props
}: DateRangeFieldProps) {
  const fromDate = parseDateString(from);
  const toDate = parseDateString(to);

  return (
    <div className={cn("@container grid w-full grid-cols-1 gap-3 @sm:grid-cols-2", className)}>
      <DateField
        {...props}
        label={fromLabel}
        value={from}
        onChange={onFromChange}
        maxDate={toDate ?? props.maxDate}
        datePlaceholder={props.datePlaceholder ?? "Start date"}
      />
      <DateField
        {...props}
        label={toLabel}
        value={to}
        onChange={onToChange}
        minDate={fromDate ?? props.minDate}
        datePlaceholder={props.datePlaceholder ?? "End date"}
      />
    </div>
  );
}
