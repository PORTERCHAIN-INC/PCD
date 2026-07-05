import { getPorterchainApiBase } from "@/lib/api-base";
import { publicEnv } from "@/lib/env";

export type AuthMe = {
  user_id: string;
  user_type: string;
  email?: string | null;
  role?: string | null;
  status?: string | null;
};

export async function fetchAuthMe(token: string): Promise<AuthMe> {
  const res = await fetch(`${getPorterchainApiBase()}/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "auth_failed");
  }
  return res.json();
}

/** Home URL for the user's portal after unified website sign-in. */
export function portalHomeUrl(userType: string): string {
  const type = userType.toLowerCase();

  if (type === "admin" || type === "dispatcher" || type === "support" || type === "sales") {
    return `${publicEnv.adminPortalUrl}/dashboard`;
  }
  if (type === "merchant") {
    return `${publicEnv.merchantPortalUrl}/onboarding`;
  }
  if (type === "driver") {
    return `${publicEnv.driverPortalUrl}/onboarding`;
  }
  return `${publicEnv.customerPortalUrl}/dashboard`;
}
