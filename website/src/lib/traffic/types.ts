export type GtaZoneId =
  | "downtown_toronto"
  | "scarborough"
  | "north_york"
  | "etobicoke"
  | "mississauga"
  | "brampton"
  | "oakville"
  | "milton"
  | "vaughan"
  | "markham"
  | "hamilton";

export type TrafficLevel = "normal" | "busy" | "peak" | "extreme";

export type TrafficMultiplierValue = 1.0 | 1.15 | 1.3 | 1.5;

export const TRAFFIC_LEVEL_MULTIPLIERS: Record<TrafficLevel, TrafficMultiplierValue> = {
  normal: 1.0,
  busy: 1.15,
  peak: 1.3,
  extreme: 1.5,
};

export type GtaZone = {
  id: GtaZoneId;
  name: string;
  fsaPrefixes: string[];
};

export type TrafficEvaluateInput = {
  postalCodes: string[];
  at?: Date | string;
};

export type ZoneTrafficDetail = {
  zone_id: GtaZoneId;
  zone_name: string;
  postal_code: string;
  traffic_level: TrafficLevel;
  traffic_multiplier: TrafficMultiplierValue;
};

export type TrafficResult = {
  traffic_level: TrafficLevel;
  traffic_multiplier: TrafficMultiplierValue;
  zones: ZoneTrafficDetail[];
  evaluated_at: string;
  day_of_week: string;
  hour_et: number;
};

export type TrafficResultCamel = {
  trafficLevel: TrafficLevel;
  trafficMultiplier: TrafficMultiplierValue;
  zones: {
    zoneId: GtaZoneId;
    zoneName: string;
    postalCode: string;
    trafficLevel: TrafficLevel;
    trafficMultiplier: TrafficMultiplierValue;
  }[];
  evaluatedAt: string;
  dayOfWeek: string;
  hourEt: number;
};
