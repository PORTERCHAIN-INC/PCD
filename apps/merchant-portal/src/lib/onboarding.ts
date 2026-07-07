import { publicEnv } from "@/lib/env";

export interface PortalOnboardingStep {
  id: string;
  label: string;
  description: string;
  complete: boolean;
  status: string;
  missing?: string[];
}

export interface PortalOnboardingStatus {
  ready: boolean;
  blockers: string[];
  status: string;
  clerk_linked: boolean;
  steps: PortalOnboardingStep[];
  pending_documents: number;
  can_access_portal: boolean;
  company_name?: string | null;
  merchant_id?: string | null;
}

export async function fetchMerchantOnboarding(token: string): Promise<PortalOnboardingStatus> {
  const res = await fetch(`${publicEnv.porterchainApiUrl}/v1/auth/merchant/onboarding`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "onboarding_fetch_failed");
  }
  return res.json();
}

export const PENDING_MERCHANT_PATHS = ["/onboarding"] as const;

export function isPendingMerchantPath(pathname: string): boolean {
  return PENDING_MERCHANT_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}
