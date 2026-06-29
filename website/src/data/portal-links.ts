import { publicEnv } from "@/lib/env";

/** Merchant portal sign-in (B2B login from public website). */
export const merchantSignInUrl = `${publicEnv.merchantPortalUrl}/sign-in`;

export const merchantPortalUrl = publicEnv.merchantPortalUrl;
export const driverPortalUrl = publicEnv.driverPortalUrl;

export function portalDisplayHost(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return url.replace(/^https?:\/\//, "").replace(/\/$/, "");
  }
}
