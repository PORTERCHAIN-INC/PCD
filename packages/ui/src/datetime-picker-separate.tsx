"use client";

import {
  addMonths,
  format,
  isBefore,
  isSameDay,
  startOfDay,
  startOfMonth,
  subMonths,
} from "date-fns";
import { Calendar, ChevronLeft, ChevronRight, Clock, Globe } from "lucide-react";
import {
  forwardRef,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type Ref,
  type RefObject,
} from "react";
import { DayPicker } from "react-day-picker";
import { cn } from "./utils";
import "./datetime-picker-separate.css";

const TIMEZONE_OPTIONS = [
  "America/Toronto",
  "America/Vancouver",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "UTC",
  "Europe/London",
] as const;

export type DateTimePickerSeparateProps = {
  value?: Date;
  onChange?: (date: Date | undefined) => void;
  disabled?: boolean;
  minDate?: Date;
  maxDate?: Date;
  datePlaceholder?: string;
  timePlaceholder?: string;
  timeInterval?: 15 | 30 | 60;
  hourFormat?: 12 | 24;
  timezone?: string;
  showTimezone?: boolean;
  onTimezoneChange?: (timezone: string) => void;
  minTime?: string;
  maxTime?: string;
  weekStartsOn?: 0 | 1 | 2 | 3 | 4 | 5 | 6;
  disabledDates?: (date: Date) => boolean;
  name?: string;
  className?: string;
};

function formatTime(hour: number, minute: number, hourFormat: 12 | 24): string {
  const min = minute.toString().padStart(2, "0");
  if (hourFormat === 24) {
    return `${hour.toString().padStart(2, "0")}:${min}`;
  }
  const period = hour >= 12 ? "PM" : "AM";
  const h = hour % 12 || 12;
  return `${h}:${min} ${period}`;
}

function toMinutes(time24: string): number {
  const [h, m] = time24.split(":");
  return parseInt(h, 10) * 60 + parseInt(m, 10);
}

function parse24h(display: string): string {
  if (!display.includes("AM") && !display.includes("PM")) return display;
  const [timePart, period] = display.split(" ");
  const [hStr, mStr] = timePart.split(":");
  let hour = parseInt(hStr, 10);
  if (period === "AM" && hour === 12) hour = 0;
  else if (period === "PM" && hour !== 12) hour += 12;
  return `${hour.toString().padStart(2, "0")}:${mStr}`;
}

function buildDate(date: Date | undefined, timeStr: string): Date | undefined {
  if (!date) return undefined;
  const time24 = parse24h(timeStr);
  const [h, m] = time24.split(":");
  if (h == null || m == null) return date;
  const next = new Date(date.getTime());
  next.setHours(parseInt(h, 10), parseInt(m, 10), 0, 0);
  return next;
}

/** `datetime-local` / form-friendly `yyyy-MM-ddTHH:mm`. */
export function toLocalDateTimeString(date: Date): string {
  return format(date, "yyyy-MM-dd'T'HH:mm");
}

export function parseLocalDateTimeString(value: string | undefined | null): Date | undefined {
  if (!value?.trim()) return undefined;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? undefined : d;
}

function useClickOutside(open: boolean, onClose: () => void, ref: RefObject<HTMLElement | null>) {
  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent) => {
      if (!ref.current?.contains(event.target as Node)) onClose();
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onClose, ref]);
}

export const DateTimePickerSeparate = forwardRef(function DateTimePickerSeparate(
  {
    value,
    onChange,
    disabled = false,
    minDate,
    maxDate,
    datePlaceholder = "Pick a date",
    timePlaceholder = "Pick time",
    timeInterval = 15,
    hourFormat = 12,
    timezone,
    showTimezone = false,
    onTimezoneChange,
    minTime,
    maxTime,
    weekStartsOn = 0,
    disabledDates: disabledDatesFn,
    name,
    className,
  }: DateTimePickerSeparateProps,
  ref: Ref<HTMLInputElement>
) {
  const dateId = useId();
  const timeId = useId();
  const dateRootRef = useRef<HTMLDivElement>(null);
  const timeRootRef = useRef<HTMLDivElement>(null);
  const timeListRef = useRef<HTMLDivElement>(null);

  const [dateOpen, setDateOpen] = useState(false);
  const [timeOpen, setTimeOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(value);
  const [month, setMonth] = useState<Date>(() => startOfMonth(value ?? new Date()));
  const [time, setTime] = useState(() =>
    value
      ? formatTime(value.getHours(), value.getMinutes(), hourFormat)
      : formatTime(9, 0, hourFormat)
  );
  const [selectedTimezone, setSelectedTimezone] = useState(timezone ?? "America/Toronto");

  useEffect(() => {
    if (!timezone) {
      setSelectedTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone);
    }
  }, [timezone]);

  useEffect(() => {
    setSelectedDate(value);
    if (value) {
      setTime(formatTime(value.getHours(), value.getMinutes(), hourFormat));
      setMonth(startOfMonth(value));
    }
  }, [value, hourFormat]);

  useEffect(() => {
    if (dateOpen) {
      setMonth(startOfMonth(selectedDate ?? minDate ?? new Date()));
    }
  }, [dateOpen, selectedDate, minDate]);

  useEffect(() => {
    if (timezone) setSelectedTimezone(timezone);
  }, [timezone]);

  useClickOutside(dateOpen, () => setDateOpen(false), dateRootRef);
  useClickOutside(timeOpen, () => setTimeOpen(false), timeRootRef);

  const timeSlots = useMemo(() => {
    const slots: string[] = [];
    const slotsPerHour = 60 / timeInterval;
    const totalSlots = 24 * slotsPerHour;
    const minMinutes = minTime ? toMinutes(parse24h(minTime)) : 0;
    const maxMinutes = maxTime ? toMinutes(parse24h(maxTime)) : 24 * 60 - 1;
    for (let i = 0; i < totalSlots; i++) {
      const hour = Math.floor(i / slotsPerHour);
      const minute = (i % slotsPerHour) * timeInterval;
      const totalMins = hour * 60 + minute;
      if (totalMins >= minMinutes && totalMins <= maxMinutes) {
        slots.push(formatTime(hour, minute, hourFormat));
      }
    }
    return slots;
  }, [timeInterval, hourFormat, minTime, maxTime]);

  useEffect(() => {
    if (!timeOpen) return;
    const selectedIndex = timeSlots.indexOf(time);
    if (selectedIndex < 0) return;
    requestAnimationFrame(() => {
      const el = timeListRef.current?.children[selectedIndex] as HTMLElement | undefined;
      el?.scrollIntoView({ block: "center" });
    });
  }, [timeOpen, time, timeSlots]);

  const isTimePast = (timeValue: string): boolean => {
    const dateToCheck = selectedDate || new Date();
    const now = new Date();
    if (!isSameDay(dateToCheck, now)) return false;
    return toMinutes(parse24h(timeValue)) <= now.getHours() * 60 + now.getMinutes();
  };

  const handleDateSelect = (date: Date | undefined) => {
    if (!date) {
      setSelectedDate(undefined);
      onChange?.(undefined);
      return;
    }
    let nextTime = time;
    if (isTimePast(time)) {
      const first = timeSlots.find((slot) => !isTimePastForDate(date, slot));
      if (first) nextTime = first;
    }
    const combined = buildDate(date, nextTime);
    setTime(nextTime);
    setSelectedDate(combined);
    onChange?.(combined);
    setDateOpen(false);
  };

  const isTimePastForDate = (date: Date, timeValue: string) => {
    const now = new Date();
    if (!isSameDay(date, now)) return false;
    return toMinutes(parse24h(timeValue)) <= now.getHours() * 60 + now.getMinutes();
  };

  const handleTimeSelect = (timeValue: string) => {
    setTime(timeValue);
    const combined = buildDate(selectedDate || new Date(), timeValue);
    setSelectedDate(combined);
    onChange?.(combined);
    setTimeOpen(false);
  };

  const dayDisabled = (date: Date) => {
    const day = startOfDay(date);
    if (minDate && isBefore(day, startOfDay(minDate))) return true;
    if (maxDate && isBefore(startOfDay(maxDate), day)) return true;
    return Boolean(disabledDatesFn?.(date));
  };

  const canGoPrev = !minDate || isBefore(startOfMonth(minDate), month);
  const canGoNext = !maxDate || isBefore(month, startOfMonth(maxDate));

  const triggerClass = cn(
    "flex h-11 w-full items-center gap-2.5 rounded-xl border border-primary/15 bg-white px-3.5 text-left text-sm font-medium text-primary shadow-sm transition-colors",
    "hover:border-secondary/35 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/30",
    "disabled:cursor-not-allowed disabled:opacity-50",
    !selectedDate && "font-normal text-muted"
  );

  return (
    <div className={cn("w-full", className)}>
      {name ? (
        <input
          ref={ref}
          type="hidden"
          name={name}
          value={selectedDate ? selectedDate.toISOString() : ""}
          readOnly
        />
      ) : null}

      <div className="flex w-full flex-nowrap items-stretch gap-2">
        <div ref={dateRootRef} className={cn("relative min-w-0 flex-1", dateOpen && "z-40")}>
          <button
            type="button"
            id={dateId}
            disabled={disabled}
            aria-haspopup="dialog"
            aria-expanded={dateOpen}
            onClick={() => {
              setTimeOpen(false);
              setDateOpen((o) => !o);
            }}
            className={cn(triggerClass, dateOpen && "border-secondary/40 ring-2 ring-secondary/20")}
          >
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-secondary/10 text-secondary">
              <Calendar className="h-3.5 w-3.5" />
            </span>
            <span className="truncate">
              {selectedDate ? format(selectedDate, "EEE, MMM d, yyyy") : datePlaceholder}
            </span>
          </button>
          {dateOpen ? (
            <div
              role="dialog"
              aria-labelledby={dateId}
              className="pc-dtp-popover absolute left-0 top-full z-50 mt-2"
            >
              <div className="pc-dtp-popover__head">
                <p className="pc-dtp-popover__eyebrow">Select date</p>
                <p className="pc-dtp-popover__title">
                  {selectedDate ? format(selectedDate, "EEEE, MMMM d") : datePlaceholder}
                </p>
              </div>
              <div className="pc-dtp-popover__toolbar">
                <button
                  type="button"
                  className="pc-dtp-popover__nav"
                  aria-label="Previous month"
                  disabled={!canGoPrev}
                  onClick={() => setMonth((m) => subMonths(m, 1))}
                >
                  <ChevronLeft className="h-4 w-4" strokeWidth={2.25} />
                </button>
                <p className="pc-dtp-popover__month">{format(month, "MMMM yyyy")}</p>
                <button
                  type="button"
                  className="pc-dtp-popover__nav"
                  aria-label="Next month"
                  disabled={!canGoNext}
                  onClick={() => setMonth((m) => addMonths(m, 1))}
                >
                  <ChevronRight className="h-4 w-4" strokeWidth={2.25} />
                </button>
              </div>
              <div className="pc-dtp-popover__body">
                <DayPicker
                  mode="single"
                  month={month}
                  onMonthChange={setMonth}
                  selected={selectedDate}
                  onSelect={handleDateSelect}
                  disabled={dayDisabled}
                  weekStartsOn={weekStartsOn}
                  startMonth={minDate}
                  endMonth={maxDate}
                  hideNavigation
                  className="pc-dtp-calendar"
                />
              </div>
            </div>
          ) : null}
        </div>

        <div
          ref={timeRootRef}
          className={cn("relative w-[9.75rem] shrink-0 sm:w-[11rem]", timeOpen && "z-40")}
        >
          <button
            type="button"
            id={timeId}
            disabled={disabled}
            aria-haspopup="listbox"
            aria-expanded={timeOpen}
            onClick={() => {
              setDateOpen(false);
              setTimeOpen((o) => !o);
            }}
            className={cn(triggerClass, timeOpen && "border-secondary/40 ring-2 ring-secondary/20")}
          >
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-secondary/10 text-secondary">
              <Clock className="h-3.5 w-3.5" />
            </span>
            <span className="truncate">{selectedDate ? time : timePlaceholder}</span>
          </button>
          {timeOpen ? (
            <div
              role="listbox"
              aria-labelledby={timeId}
              className="absolute right-0 top-full z-50 mt-2 max-h-72 w-full overflow-y-auto rounded-2xl border border-primary/10 bg-white p-2 shadow-xl shadow-primary/12"
            >
              <div ref={timeListRef} className="flex flex-col gap-1">
                {timeSlots.map((slot) => {
                  const past = isTimePast(slot);
                  const selected = slot === time;
                  return (
                    <button
                      key={slot}
                      type="button"
                      role="option"
                      aria-selected={selected}
                      disabled={past}
                      onClick={() => handleTimeSelect(slot)}
                      className={cn(
                        "rounded-lg px-2 py-2 text-center text-sm font-medium transition-colors",
                        selected
                          ? "bg-secondary text-white shadow-sm shadow-secondary/25"
                          : "text-primary hover:bg-secondary/10",
                        past && "cursor-not-allowed opacity-35 hover:bg-transparent"
                      )}
                    >
                      {slot}
                    </button>
                  );
                })}
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {showTimezone ? (
        <label className="relative mt-2 flex h-11 w-full items-center gap-2 rounded-xl border border-primary/15 bg-white px-3 text-sm text-primary">
          <Globe className="h-4 w-4 shrink-0 text-secondary" />
          <select
            disabled={disabled}
            value={selectedTimezone}
            onChange={(e) => {
              setSelectedTimezone(e.target.value);
              onTimezoneChange?.(e.target.value);
            }}
            className="w-full min-w-0 appearance-none bg-transparent outline-none"
            aria-label="Timezone"
          >
            {TIMEZONE_OPTIONS.map((tz) => (
              <option key={tz} value={tz}>
                {tz.replace(/_/g, " ")}
              </option>
            ))}
            {!TIMEZONE_OPTIONS.includes(selectedTimezone as (typeof TIMEZONE_OPTIONS)[number]) ? (
              <option value={selectedTimezone}>{selectedTimezone}</option>
            ) : null}
          </select>
        </label>
      ) : null}
    </div>
  );
});

DateTimePickerSeparate.displayName = "DateTimePickerSeparate";

/** Controlled string bridge for existing `datetime-local` form state. */
export function DateTimePickerSeparateField({
  value,
  onChange,
  ...props
}: Omit<DateTimePickerSeparateProps, "value" | "onChange"> & {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <DateTimePickerSeparate
      {...props}
      value={parseLocalDateTimeString(value)}
      onChange={(date) => onChange(date ? toLocalDateTimeString(date) : "")}
    />
  );
}
