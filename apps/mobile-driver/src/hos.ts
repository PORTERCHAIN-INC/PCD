/**
 * Doc 80 §2 phone HOS log (O. Reg. 555/06). Duty status from app events; "driving" when GPS
 * speed > 10 km/h. Timestamps are the phone clock at the event and go through the one offline
 * queue (action "hos_event"); the server never rewrites them on sync.
 */
import { enqueueOfflineAction, newClientId } from "./offline";

export type HosStatus = "on_duty" | "driving" | "off_duty";

export const DRIVING_KMH = 10;

/** Next status from a GPS speed sample while on shift, or null when it doesn't change. */
export function statusFromSpeed(
  current: HosStatus,
  speedMps: number | null | undefined
): HosStatus | null {
  if (current === "off_duty" || speedMps == null) return null;
  const driving = speedMps * 3.6 > DRIVING_KMH;
  if (driving && current !== "driving") return "driving";
  if (!driving && current === "driving") return "on_duty";
  return null;
}

export function hosPayload(
  status: HosStatus,
  extra: { other_operator_today?: boolean } = {},
  now = new Date()
) {
  return { client_id: newClientId(), status, at: now.toISOString(), ...extra };
}

export function logHos(status: HosStatus, extra: { other_operator_today?: boolean } = {}) {
  return enqueueOfflineAction("hos_event", hosPayload(status, extra));
}
