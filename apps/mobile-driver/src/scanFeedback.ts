/**
 * Scan feedback: beep + haptic per result. Never throws, never blocks scanning.
 * Sounds respect the phone's silent switch; haptics respect Settings → Haptics.
 */
import { createAudioPlayer, type AudioPlayer } from "expo-audio";

import { haptic } from "./haptics";

export type ScanOutcome = "ok" | "done" | "queued" | "warn" | "error";

type Sound = "ok" | "warn" | "error";

// Static requires (Metro bundles them); resolved lazily so tests/web never crash.
function source(kind: Sound) {
  if (kind === "ok") return require("../assets/sounds/scan-ok.wav");
  if (kind === "warn") return require("../assets/sounds/scan-warn.wav");
  return require("../assets/sounds/scan-error.wav");
}

const players: Partial<Record<Sound, AudioPlayer>> = {};

function play(kind: Sound) {
  try {
    const p = (players[kind] ??= createAudioPlayer(source(kind)));
    void p.seekTo(0);
    p.play();
  } catch {
    /* no audio engine (tests / web) */
  }
}

export function scanFeedback(outcome: ScanOutcome) {
  switch (outcome) {
    case "ok":
    case "queued":
      play("ok");
      haptic.tap();
      return;
    case "done":
      play("ok");
      haptic.success();
      return;
    case "warn":
      play("warn");
      haptic.warn();
      return;
    default:
      play("error");
      haptic.error();
  }
}

/** Last known fix only (instant, never prompts). Null when location is off. */
export async function scanFix(): Promise<{ lat: number; lng: number; accuracy_m?: number } | null> {
  try {
    const Location = await import("expo-location");
    const perm = await Location.getForegroundPermissionsAsync();
    if (perm.status !== "granted") return null;
    const pos = await Location.getLastKnownPositionAsync({ maxAge: 5 * 60_000 });
    if (!pos) return null;
    return {
      lat: pos.coords.latitude,
      lng: pos.coords.longitude,
      accuracy_m: pos.coords.accuracy ?? undefined,
    };
  } catch {
    return null;
  }
}

/** Same label seen again within the window = one scan (continuous camera fires many frames). */
export function makeDeduper(windowMs = 2500) {
  const seen = new Map<string, number>();
  return (code: string, now = Date.now()): boolean => {
    for (const [k, t] of seen) if (now - t > windowMs) seen.delete(k);
    if (seen.has(code)) return false;
    seen.set(code, now);
    return true;
  };
}
