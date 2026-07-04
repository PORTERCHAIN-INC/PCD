/**
 * Architecture verification — client map module MUST NOT call routing engines directly.
 *
 * | Concern            | Provider    | Client role        |
 * |--------------------|-------------|--------------------|
 * | Map tiles/render   | Google Maps | Display only       |
 * | Live GPS / tracking| Fleetbase   | Render API coords  |
 * | ETA legs           | OSRM        | Render API polyline|
 * | Optimized route    | Valhalla    | Render API polyline|
 * | Geofences          | API         | Render circles     |
 * | Traffic overlay    | Google Maps | showsTraffic prop  |
 */

export const MAP_ARCHITECTURE = {
  mapDisplay: "google_maps",
  trackingProvider: "fleetbase",
  etaEngine: "osrm",
  optimizationEngine: "valhalla",
} as const;

export function verifyRoutingEngines(engines?: {
  gps?: string;
  eta?: string;
  optimized_route?: string;
  map_display?: string;
}): { valid: boolean; violations: string[] } {
  const violations: string[] = [];
  if (!engines) return { valid: true, violations };

  if (engines.map_display && engines.map_display !== "google_maps") {
    violations.push(`map_display must be google_maps, got ${engines.map_display}`);
  }
  if (engines.gps && engines.gps !== "fleetbase" && engines.gps !== "porterchain_ping") {
    violations.push(`gps should be fleetbase adapter output, got ${engines.gps}`);
  }
  if (engines.eta && engines.eta !== "osrm") {
    violations.push(`eta should be osrm, got ${engines.eta}`);
  }
  if (engines.optimized_route && engines.optimized_route !== "valhalla") {
    violations.push(`optimized_route should be valhalla, got ${engines.optimized_route}`);
  }

  return { valid: violations.length === 0, violations };
}
