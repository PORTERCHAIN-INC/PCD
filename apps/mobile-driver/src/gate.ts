import type { Handshake } from "./types";
import { humanDriverError } from "./auth/errors";
import { isOnboardingBlocked } from "./handshake";

export type GateResult = { ok: true } | { ok: false; reason: string };

export function canEnterRoute(
  handshake: Handshake,
  signedIn: boolean,
  allowDev: boolean
): GateResult {
  if (handshake.api !== "up") {
    return {
      ok: false,
      reason:
        humanDriverError(handshake.error) || "API unreachable — start Porterchain API on :8001",
    };
  }
  if (handshake.auth !== "up" && !isOnboardingBlocked(handshake.error)) {
    return {
      ok: false,
      reason: humanDriverError(handshake.error) || "Sign-in failed — van is not on the network",
    };
  }
  if (!signedIn && !allowDev) {
    return { ok: false, reason: "Sign in required" };
  }
  return { ok: true };
}
