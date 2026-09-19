import { PHASE2_FLAG_ENV_KEYS, anyPhase2Enabled, readPhase2Flags } from "./phase2.mjs";

export type Phase2FlagKey = (typeof PHASE2_FLAG_ENV_KEYS)[number];

export type Phase2Flags = {
  crm: boolean;
  routeCenter: boolean;
  aiDispatch: boolean;
  analytics: boolean;
  intelligence: boolean;
};

export { PHASE2_FLAG_ENV_KEYS, anyPhase2Enabled, readPhase2Flags };
