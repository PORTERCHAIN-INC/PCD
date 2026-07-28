import { getPorterchainApiBase } from "@/lib/api-base";
import { customerPortalDashboardUrl } from "@/data/portal-links";

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

/**
 * Website `/login` uses the customer Clerk app only.
 * After sign-in, send provisioned customers to the customer portal dashboard.
 * Non-customer types cannot receive a cross-portal Clerk session from this page.
 */
export function customerPortalHomeUrl(): string {
  return customerPortalDashboardUrl;
}

export function isCustomerUserType(userType: string): boolean {
  return userType.toLowerCase() === "customer";
}
