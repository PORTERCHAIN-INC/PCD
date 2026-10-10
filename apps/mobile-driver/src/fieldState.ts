import type { Handshake } from "./types";

/**
 * Offline, runHandshake returns an empty "idle" handshake (no route, off duty). Applying it
 * would wipe the stop off the screen and stop GPS mid-route, so keep the last known field
 * state and only flag the connection as down.
 */
export function mergeOfflineHandshake(
  prev: Handshake,
  next: Handshake,
  signedIn: boolean
): Handshake {
  if (next.api === "down" && signedIn && (prev.online || Boolean(prev.routeId))) {
    return { ...prev, api: "down", error: null };
  }
  return next;
}
