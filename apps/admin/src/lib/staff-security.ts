/** Staff security-status client (passkey gate + event feed). */

import { adminFetch } from "@/lib/api";
import { STAFF_COOKIE_TOKEN } from "@/lib/staff-session";

/** Dispatched after passkey register/remove so the recommend banner refreshes. */
export const STAFF_PASSKEY_EVENT = "pc-staff-passkey";

export function notifyStaffPasskeyChanged(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(STAFF_PASSKEY_EVENT));
  }
}

export type StaffSecurityEvent = {
  ts: number;
  kind: string;
  detail?: Record<string, unknown>;
};

export type StaffSecurityStatus = {
  passkey_count: number;
  passkey_recommended: boolean;
  events: StaffSecurityEvent[];
  cookie_posture?: {
    domain_mode: string;
    secure: boolean;
    samesite: string;
    httponly: boolean;
    domain: string | null;
  };
};

export function fetchStaffSecurityStatus(
  token: string = STAFF_COOKIE_TOKEN
): Promise<StaffSecurityStatus> {
  return adminFetch<StaffSecurityStatus>("/v1/auth/staff/security-status", token);
}
