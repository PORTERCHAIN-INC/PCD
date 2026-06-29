"use client";

import { useEffect, useId, useRef, useState } from "react";
import { DayPicker } from "react-day-picker";
import {
  format,
  setHours,
  setMinutes,
  startOfDay,
  isToday,
  isBefore,
} from "date-fns";
import { enCA, frCA } from "date-fns/locale";
import { Calendar, Clock } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

const TIME_SLOTS = buildTimeSlots(30, 6, 22);

function buildTimeSlots(intervalMinutes: number, startHour: number, endHour: number) {
  const slots: string[] = [];
  for (let hour = startHour; hour <= endHour; hour++) {
    for (let minute = 0; minute < 60; minute += intervalMinutes) {
      if (hour === endHour && minute > 0) break;
      slots.push(
        `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`
      );
    }
  }
  return slots;
}

function parseTime(time: string) {
  const [hours, minutes] = time.split(":").map(Number);
  return { hours, minutes };
}

function combineDateAndTime(date: Date, time: string) {
  const { hours, minutes } = parseTime(time);
  return setMinutes(setHours(startOfDay(date), hours), minutes);
}

function slotsAvailableOnDate(date: Date) {
  if (!isToday(date)) return TIME_SLOTS;
  return TIME_SLOTS.filter((slot) => {
    const { hours, minutes } = parseTime(slot);
    const slotDate = setMinutes(setHours(date, hours), minutes);
    return !isBefore(slotDate, new Date());
  });
}

function getNextAvailableSlot(date: Date, slots: string[]) {
  return slots[0] ?? "09:00";
}

interface ScheduleDateTimePickerProps {
  value: Date;
  onChange: (value: Date) => void;
}

export default function ScheduleDateTimePicker({
  value,
  onChange,
}: ScheduleDateTimePickerProps) {
  const t = useTranslations("booking.schedulePicker");
  const locale = useLocale();
  const dateFnsLocale = locale === "fr" ? frCA : enCA;
  const calendarId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const [calendarOpen, setCalendarOpen] = useState(false);

  const selectedTime = format(value, "HH:mm");

  const availableTimeSlots = slotsAvailableOnDate(value);

  const displayTime = availableTimeSlots.includes(selectedTime)
    ? selectedTime
    : getNextAvailableSlot(value, availableTimeSlots);

  useEffect(() => {
    if (!availableTimeSlots.includes(selectedTime) && availableTimeSlots.length > 0) {
      onChange(combineDateAndTime(value, getNextAvailableSlot(value, availableTimeSlots)));
    }
  }, [availableTimeSlots, onChange, selectedTime, value]);

  useEffect(() => {
    if (!calendarOpen) return;

    const handlePointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setCalendarOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setCalendarOpen(false);
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [calendarOpen]);

  const handleDateSelect = (date: Date | undefined) => {
    if (!date) return;
    const slots = slotsAvailableOnDate(date);
    onChange(combineDateAndTime(date, getNextAvailableSlot(date, slots)));
    setCalendarOpen(false);
  };

  const handleTimeChange = (time: string) => {
    onChange(combineDateAndTime(value, time));
  };

  return (
    <motion.div
      ref={rootRef}
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className="space-y-2"
    >
      <div className="grid grid-cols-1 sm:grid-cols-[1.2fr_1fr] gap-2">
        <div className="relative">
          <button
            type="button"
            id={calendarId}
            aria-haspopup="dialog"
            aria-expanded={calendarOpen}
            aria-label={t("pickDate")}
            onClick={() => setCalendarOpen((open) => !open)}
            className="booking-schedule-field w-full"
          >
            <Calendar className="w-4 h-4 text-secondary shrink-0" />
            <span className="truncate">
              {format(value, "EEE, MMM d, yyyy", { locale: dateFnsLocale })}
            </span>
          </button>

          {calendarOpen && (
            <div
              role="dialog"
              aria-labelledby={calendarId}
              className="booking-schedule-calendar absolute left-0 right-0 z-30 mt-2 rounded-2xl border border-gray-200/80 bg-white p-3 shadow-xl shadow-primary/10"
            >
              <DayPicker
                mode="single"
                selected={value}
                onSelect={handleDateSelect}
                locale={dateFnsLocale}
                weekStartsOn={0}
                disabled={{ before: startOfDay(new Date()) }}
                classNames={{
                  root: "booking-day-picker",
                  months: "flex flex-col",
                  month: "space-y-3",
                  month_caption: "flex items-center justify-center relative px-8",
                  caption_label: "text-sm font-semibold text-primary",
                  nav: "flex items-center gap-1",
                  button_previous:
                    "absolute left-0 top-1/2 -translate-y-1/2 inline-flex h-8 w-8 items-center justify-center rounded-full text-muted hover:bg-gray-bg hover:text-primary",
                  button_next:
                    "absolute right-0 top-1/2 -translate-y-1/2 inline-flex h-8 w-8 items-center justify-center rounded-full text-muted hover:bg-gray-bg hover:text-primary",
                  weekdays: "grid grid-cols-7 gap-1",
                  weekday:
                    "text-center text-[0.7rem] font-semibold uppercase tracking-wide text-muted",
                  week: "mt-1 grid grid-cols-7 gap-1",
                  day: "flex items-center justify-center",
                  day_button: cn(
                    "h-9 w-9 rounded-full text-sm font-medium text-primary transition-colors",
                    "hover:bg-secondary/10 hover:text-secondary",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/30"
                  ),
                  selected:
                    "[&>button]:bg-secondary [&>button]:text-white [&>button]:hover:bg-secondary [&>button]:hover:text-white",
                  today: "[&>button]:ring-1 [&>button]:ring-secondary/30",
                  outside: "[&>button]:text-muted/40",
                  disabled: "[&>button]:text-muted/30 [&>button]:hover:bg-transparent",
                }}
              />
            </div>
          )}
        </div>

        <label className="booking-schedule-field cursor-pointer">
          <Clock className="w-4 h-4 text-secondary shrink-0" />
          <select
            value={displayTime}
            onChange={(e) => handleTimeChange(e.target.value)}
            aria-label={t("pickTime")}
            className="w-full min-w-0 bg-transparent text-base text-primary outline-none cursor-pointer appearance-none"
          >
            {availableTimeSlots.map((slot) => (
              <option key={slot} value={slot}>
                {format(combineDateAndTime(value, slot), "h:mm a", {
                  locale: dateFnsLocale,
                })}
              </option>
            ))}
          </select>
        </label>
      </div>

      <p className="type-caption normal-case tracking-normal text-muted px-1">
        {t("timezoneNote")}
      </p>
    </motion.div>
  );
}

export function createDefaultScheduledAt() {
  const date = new Date();
  date.setDate(date.getDate() + 1);
  date.setHours(9, 0, 0, 0);
  return date;
}
