/** Staff security-status client (passkey gate + event feed). */

import { adminFetch } from "@/lib/api";
import { STAFF_COOKIE_TOKEN } from "@/lib/staff-session";

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
