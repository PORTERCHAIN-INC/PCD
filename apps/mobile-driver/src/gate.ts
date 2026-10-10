import { isOnboardingBlocked } from "./handshake";
import type { Handshake } from "./types";

export type GateResult = { ok: true } | { ok: false; reason: string };

/** Fail-closed: the field app opens only when the API answered and this driver is signed in. */
export function canEnterRoute(
  handshake: Handshake,
  signedIn: boolean,
  allowDev: boolean
): GateResult {
  if (handshake.api !== "up")
    return { ok: false, reason: handshake.error ?? "network_unavailable" };
  if (handshake.auth !== "up" && !isOnboardingBlocked(handshake.error)) {
    return { ok: false, reason: handshake.error ?? "sign_in_failed" };
  }
  if (!signedIn && !allowDev) return { ok: false, reason: "Sign in required" };
  return { ok: true };
}
