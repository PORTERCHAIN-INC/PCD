/** Phase 2 feature flags — default off (masterrule §21.4 · §1.2.4). */

export const PHASE2_FLAG_ENV_KEYS = [
  "PORTERCHAIN_PHASE2_CRM",
  "PORTERCHAIN_PHASE2_ROUTE_CENTER",
  "PORTERCHAIN_PHASE2_AI_DISPATCH",
  "PORTERCHAIN_PHASE2_ANALYTICS",
  "PORTERCHAIN_PHASE2_INTELLIGENCE",
];

function envBool(value) {
  if (!value) return false;
  const normalized = value.trim().toLowerCase();
  return normalized === "1" || normalized === "true" || normalized === "yes" || normalized === "on";
}

/** @param {Record<string, string | undefined>} [env] */
export function readPhase2Flags(env = process.env) {
  return {
    crm: envBool(env.PORTERCHAIN_PHASE2_CRM),
    routeCenter: envBool(env.PORTERCHAIN_PHASE2_ROUTE_CENTER),
    aiDispatch: envBool(env.PORTERCHAIN_PHASE2_AI_DISPATCH),
    analytics: envBool(env.PORTERCHAIN_PHASE2_ANALYTICS),
    intelligence: envBool(env.PORTERCHAIN_PHASE2_INTELLIGENCE),
  };
}

/** @param {{ crm: boolean; routeCenter: boolean; aiDispatch: boolean; analytics: boolean; intelligence: boolean }} flags */
export function anyPhase2Enabled(flags) {
  return (
    flags.crm || flags.routeCenter || flags.aiDispatch || flags.analytics || flags.intelligence
  );
}
