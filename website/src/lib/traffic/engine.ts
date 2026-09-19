import { normalizePostalCodes } from "./postal";
import {
  applyZoneTrafficLevel,
  getBaseTrafficLevel,
  getTorontoParts,
  maxTrafficLevel,
} from "./schedules";
import {
  TRAFFIC_LEVEL_MULTIPLIERS,
  type GtaZoneId,
  type TrafficEvaluateInput,
  type TrafficLevel,
  type TrafficMultiplierValue,
  type TrafficResult,
  type TrafficResultCamel,
  type ZoneTrafficDetail,
} from "./types";
import { resolveZoneByFsa } from "./zones";

export class GtaTrafficEngine {
  evaluate(input: TrafficEvaluateInput): TrafficResult {
    const at = input.at ? new Date(input.at) : new Date();
    const fsas = normalizePostalCodes(input.postalCodes);
    const { dayKind, dayOfWeek, hour, minute } = getTorontoParts(at);
    const baseLevel = getBaseTrafficLevel(dayKind, hour, minute);

    const zones: ZoneTrafficDetail[] = [];

    for (const fsa of fsas) {
      const zone = resolveZoneByFsa(fsa);
      if (!zone) continue;

      const traffic_level = applyZoneTrafficLevel(baseLevel, zone.id, hour, minute);
      zones.push({
        zone_id: zone.id,
        zone_name: zone.name,
        postal_code: fsa,
        traffic_level,
        traffic_multiplier: TRAFFIC_LEVEL_MULTIPLIERS[traffic_level],
      });
    }

    const traffic_level =
      zones.length > 0 ? maxTrafficLevel(zones.map((z) => z.traffic_level)) : baseLevel;

    const traffic_multiplier = TRAFFIC_LEVEL_MULTIPLIERS[traffic_level];

    return {
      traffic_level,
      traffic_multiplier,
      zones,
      evaluated_at: at.toISOString(),
      day_of_week: dayOfWeek,
      hour_et: hour,
    };
  }

  getMultiplier(input: TrafficEvaluateInput): TrafficMultiplierValue {
    return this.evaluate(input).traffic_multiplier;
  }
}

export const gtaTrafficEngine = new GtaTrafficEngine();

export function toCamelCaseTrafficResult(result: TrafficResult): TrafficResultCamel {
  return {
    trafficLevel: result.traffic_level,
    trafficMultiplier: result.traffic_multiplier,
    zones: result.zones.map((z) => ({
      zoneId: z.zone_id,
      zoneName: z.zone_name,
      postalCode: z.postal_code,
      trafficLevel: z.traffic_level,
      trafficMultiplier: z.traffic_multiplier,
    })),
    evaluatedAt: result.evaluated_at,
    dayOfWeek: result.day_of_week,
    hourEt: result.hour_et,
  };
}

export function trafficLevelLabel(level: TrafficLevel): string {
  return {
    normal: "Normal",
    busy: "Busy",
    peak: "Peak",
    extreme: "Extreme",
  }[level];
}
