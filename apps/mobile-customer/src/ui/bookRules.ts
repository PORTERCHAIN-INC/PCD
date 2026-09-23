import type { Address } from "../api";

export function startOfDay(date: Date): Date {
  const next = new Date(date);
  next.setHours(0, 0, 0, 0);
  return next;
}

export function dayChoices(count = 7, now = new Date()): Date[] {
  const start = startOfDay(now);
  return Array.from({ length: count }, (_, index) => {
    const day = new Date(start);
    day.setDate(start.getDate() + index);
    return day;
  });
}

/** Half-hour pickup times from 06:00 through 22:00, local, still ahead of now. */
export function slotsFor(day: Date, now = new Date()): string[] {
  const earliest = now.getTime() + 15 * 60_000;
  const slots: string[] = [];
  for (let minutes = 6 * 60; minutes <= 22 * 60; minutes += 30) {
    const slot = new Date(day);
    slot.setHours(Math.floor(minutes / 60), minutes % 60, 0, 0);
    if (slot.getTime() > earliest) slots.push(slot.toISOString());
  }
  return slots;
}

export function dayLabel(day: Date, now = new Date()): string {
  const today = startOfDay(now);
  const target = startOfDay(day);
  if (target.getTime() === today.getTime()) return "Today";
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);
  if (target.getTime() === tomorrow.getTime()) return "Tomorrow";
  return day.toLocaleDateString("en-CA", { weekday: "short", month: "short", day: "numeric" });
}

export function timeLabel(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-CA", { hour: "numeric", minute: "2-digit" });
}

export function addressReady(address: Address): boolean {
  if (!address.formatted.trim()) return false;
  return address.lat != null && address.lng != null;
}

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
