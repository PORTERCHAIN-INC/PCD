import { publicEnv } from "@/lib/env";

export interface MerchantVerticalOption {
  slug: string;
  label: string;
}

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
  vertical?: string | null;
  vertical_label?: string | null;
  vertical_options?: MerchantVerticalOption[];
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

export async function saveMerchantVertical(
  token: string,
  vertical: string
): Promise<PortalOnboardingStatus> {
  const res = await fetch(`${publicEnv.porterchainApiUrl}/v1/auth/merchant/onboarding/vertical`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ vertical }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "vertical_save_failed");
  }
  return res.json();
}

export const PENDING_MERCHANT_PATHS = ["/onboarding"] as const;

export function isPendingMerchantPath(pathname: string): boolean {
  return PENDING_MERCHANT_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}
