import type { GtaZoneId, TrafficLevel } from "./types";

type DayKind = "weekday" | "saturday" | "sunday";

type TimeWindow = {
  startHour: number;
  endHour: number;
  level: TrafficLevel;
};

/** Base schedule before zone-specific bumps */
const BASE_SCHEDULES: Record<DayKind, TimeWindow[]> = {
  weekday: [
    { startHour: 0, endHour: 6, level: "normal" },
    { startHour: 6, endHour: 8, level: "busy" },
    { startHour: 8, endHour: 10, level: "peak" },
    { startHour: 10, endHour: 15, level: "busy" },
    { startHour: 15, endHour: 16.5, level: "busy" },
    { startHour: 16.5, endHour: 19, level: "peak" },
    { startHour: 19, endHour: 21, level: "busy" },
    { startHour: 21, endHour: 24, level: "normal" },
  ],
  saturday: [
    { startHour: 0, endHour: 9, level: "normal" },
    { startHour: 9, endHour: 13, level: "busy" },
    { startHour: 13, endHour: 17, level: "busy" },
    { startHour: 17, endHour: 24, level: "normal" },
  ],
  sunday: [
    { startHour: 0, endHour: 11, level: "normal" },
    { startHour: 11, endHour: 16, level: "busy" },
    { startHour: 16, endHour: 24, level: "normal" },
  ],
};

/**
 * Zone-specific rush-hour intensity bumps during peak windows.
 * Downtown core hits extreme; 401-corridor suburbs peak → extreme AM/PM.
 */
const ZONE_PEAK_BUMPS: Partial<
  Record<GtaZoneId, { amExtreme?: boolean; pmExtreme?: boolean; peakToExtreme?: boolean }>
> = {
  downtown_toronto: { amExtreme: true, pmExtreme: true, peakToExtreme: true },
  scarborough: { pmExtreme: true },
  north_york: { amExtreme: true, pmExtreme: true },
  etobicoke: { amExtreme: true, pmExtreme: true },
  mississauga: { amExtreme: true, pmExtreme: true },
  brampton: { amExtreme: true, pmExtreme: true },
  vaughan: { amExtreme: true, pmExtreme: true },
  markham: { amExtreme: true, pmExtreme: true },
  oakville: { amExtreme: true, pmExtreme: true },
  milton: { amExtreme: true, pmExtreme: true },
  hamilton: { pmExtreme: true },
};

const LEVEL_RANK: Record<TrafficLevel, number> = {
  normal: 0,
  busy: 1,
  peak: 2,
  extreme: 3,
};

export function getTorontoParts(date: Date): {
  dayKind: DayKind;
  dayOfWeek: string;
  hour: number;
  minute: number;
} {
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Toronto",
    weekday: "long",
    hour: "numeric",
    minute: "numeric",
    hour12: false,
  });

  const parts = formatter.formatToParts(date);
  const weekday = parts.find((p) => p.type === "weekday")?.value ?? "Monday";
  const hour = parseInt(parts.find((p) => p.type === "hour")?.value ?? "0", 10);
  const minute = parseInt(parts.find((p) => p.type === "minute")?.value ?? "0", 10);

  let dayKind: DayKind = "weekday";
  if (weekday === "Saturday") dayKind = "saturday";
  if (weekday === "Sunday") dayKind = "sunday";

  return { dayKind, dayOfWeek: weekday, hour, minute };
}

export function getBaseTrafficLevel(dayKind: DayKind, hour: number, minute: number): TrafficLevel {
  const time = hour + minute / 60;
  const windows = BASE_SCHEDULES[dayKind];

  for (const window of windows) {
    if (time >= window.startHour && time < window.endHour) {
      return window.level;
    }
  }

  return "normal";
}

export function applyZoneTrafficLevel(
  baseLevel: TrafficLevel,
  zoneId: GtaZoneId,
  hour: number,
  minute: number
): TrafficLevel {
  const time = hour + minute / 60;
  const bumps = ZONE_PEAK_BUMPS[zoneId];
  if (!bumps) return baseLevel;

  let level = baseLevel;

  const isAmRush = time >= 7.5 && time < 10;
  const isPmRush = time >= 16 && time < 19;

  if (bumps.peakToExtreme && level === "peak") {
    level = "extreme";
  }

  if (bumps.amExtreme && isAmRush) {
    level = maxLevel(level, "extreme");
  }

  if (bumps.pmExtreme && isPmRush) {
    level = maxLevel(level, "extreme");
  }

  if (isAmRush || isPmRush) {
    level = maxLevel(level, "peak");
  }

  return level;
}

function maxLevel(a: TrafficLevel, b: TrafficLevel): TrafficLevel {
  return LEVEL_RANK[a] >= LEVEL_RANK[b] ? a : b;
}

export function maxTrafficLevel(levels: TrafficLevel[]): TrafficLevel {
  return levels.reduce<TrafficLevel>(
    (max, level) => (LEVEL_RANK[level] > LEVEL_RANK[max] ? level : max),
    "normal"
  );
}
