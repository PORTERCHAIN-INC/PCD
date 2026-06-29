export {
  GtaTrafficEngine,
  gtaTrafficEngine,
  toCamelCaseTrafficResult,
  trafficLevelLabel,
} from "./engine";
export { extractFsa, normalizePostalCodes } from "./postal";
export { GTA_ZONES, resolveZoneByFsa, getZoneById } from "./zones";
export { TRAFFIC_LEVEL_MULTIPLIERS } from "./types";
export type {
  GtaZoneId,
  GtaZone,
  TrafficLevel,
  TrafficMultiplierValue,
  TrafficEvaluateInput,
  TrafficResult,
  TrafficResultCamel,
  ZoneTrafficDetail,
} from "./types";
