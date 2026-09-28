import type { OrderFilters } from "@/lib/orders";

export type OrderPeriod = "today" | "yesterday" | "last7" | "last_month" | "custom" | "all";
export type OrderQueue = "needs_decision" | "on_the_road" | "open" | "done";

const OPEN_QUEUES = new Set<OrderQueue>(["needs_decision", "on_the_road", "open"]);

type Ymd = { y: number; m: number; d: number };

function torontoToday(now = new Date()): Ymd {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Toronto",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(now);
  const pick = (type: string) => Number(parts.find((part) => part.type === type)?.value);
  return { y: pick("year"), m: pick("month"), d: pick("day") };
}

function iso(day: Ymd): string {
  return `${day.y}-${String(day.m).padStart(2, "0")}-${String(day.d).padStart(2, "0")}`;
}

function addDays(day: Ymd, delta: number): Ymd {
  const next = new Date(Date.UTC(day.y, day.m - 1, day.d + delta));
  return { y: next.getUTCFullYear(), m: next.getUTCMonth() + 1, d: next.getUTCDate() };
}

export function periodDates(
  period: OrderPeriod,
  customFrom: string,
  customTo: string,
  now = new Date()
): { date_from?: string; date_to?: string } {
  const today = torontoToday(now);
  if (period === "all") return {};
  if (period === "today") {
    const day = iso(today);
    return { date_from: day, date_to: day };
  }
  if (period === "yesterday") {
    const day = iso(addDays(today, -1));
    return { date_from: day, date_to: day };
  }
  if (period === "last7") {
    return { date_from: iso(addDays(today, -6)), date_to: iso(today) };
  }
  if (period === "last_month") {
    const firstThis = { y: today.y, m: today.m, d: 1 };
    const lastPrev = addDays(firstThis, -1);
    return { date_from: iso({ y: lastPrev.y, m: lastPrev.m, d: 1 }), date_to: iso(lastPrev) };
  }
  const from = customFrom.trim();
  const to = customTo.trim();
  if (!from && !to) return {};
  return { date_from: from || to, date_to: to || from };
}

export function boardQuery(
  period: OrderPeriod,
  queue: OrderQueue | "",
  customFrom: string,
  customTo: string,
  state?: string
): Pick<OrderFilters, "date_from" | "date_to" | "date_field" | "queue" | "include_carryover"> {
  const dates = periodDates(period, customFrom, customTo);
  const hasWindow = Boolean(dates.date_from || dates.date_to);
  const openQueue = queue !== "" && OPEN_QUEUES.has(queue);
  return {
    date_from: dates.date_from,
    date_to: dates.date_to,
    date_field: hasWindow ? "scheduled" : undefined,
    queue: state || !queue ? undefined : queue,
    include_carryover: hasWindow && openQueue && !state ? true : undefined,
  };
}

export function boardSummary(
  period: OrderPeriod,
  queue: OrderQueue | "",
  state: string | undefined,
  customFrom: string,
  customTo: string
): string {
  const periodLabel: Record<OrderPeriod, string> = {
    today: "Today",
    yesterday: "Yesterday",
    last7: "Last 7 days",
    last_month: "Last month",
    custom: "Custom dates",
    all: "Any time",
  };
  const queueLabel: Record<OrderQueue, string> = {
    needs_decision: "Needs a decision",
    on_the_road: "On the road",
    open: "All open",
    done: "Done",
  };
  const dates = periodDates(period, customFrom, customTo);
  const when =
    period === "custom" && dates.date_from
      ? dates.date_from === dates.date_to
        ? dates.date_from
        : `${dates.date_from} – ${dates.date_to}`
      : periodLabel[period];
  const work = state ? state.replace(/_/g, " ") : queue ? queueLabel[queue] : "Any status";
  const carry =
    !state && queue !== "" && OPEN_QUEUES.has(queue) && dates.date_from
      ? " Older unfinished orders stay on this list."
      : "";
  return `${when} · ${work}.${carry}`;
}
