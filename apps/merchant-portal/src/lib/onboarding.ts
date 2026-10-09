import { merchantStatusLabel } from "@/lib/catalog";
import { publicEnv } from "@/lib/env";
import { waitCopy, askOwnerForCompanyFile } from "@/lib/onboarding-copy";

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
  status_label?: string;
  missing?: string[];
}

export interface CompanyFileCompleteness {
  complete: boolean;
  missing: string[];
  missing_labels: string[];
  can_edit: boolean;
}

export interface CompanyFileSnapshot {
  company_name?: string | null;
  legal_name?: string | null;
  email?: string | null;
  phone?: string | null;
  hst_number?: string | null;
  billing_address?: { formatted?: string; postal?: string; place_id?: string } | null;
}

export interface PortalOnboardingStatus {
  ready: boolean;
  blockers: string[];
  status: string;
  status_label?: string | null;
  clerk_linked: boolean;
  steps: PortalOnboardingStep[];
  pending_documents: number;
  can_access_portal: boolean;
  company_name?: string | null;
  merchant_id?: string | null;
  role?: string | null;
  role_label?: string | null;
  can_edit_company?: boolean;
  completeness?: CompanyFileCompleteness | null;
  company_file?: CompanyFileSnapshot | null;
  signup_url?: string | null;
  logo_url?: string | null;
  vertical?: string | null;
  vertical_label?: string | null;
  vertical_options?: MerchantVerticalOption[];
}

export type CompanyFileUpdate = {
  company_name?: string;
  legal_name?: string;
  phone?: string;
  hst_number?: string;
  billing_address?: {
    formatted: string;
    postal?: string;
    place_id?: string;
    lat?: number;
    lng?: number;
  };
};

function onboardingError(body: { detail?: unknown }, fallback: string): Error {
  return new Error(typeof body.detail === "string" ? body.detail : fallback);
}

export async function fetchMerchantOnboarding(token: string): Promise<PortalOnboardingStatus> {
  const res = await fetch(`${publicEnv.porterchainApiUrl}/v1/auth/merchant/onboarding`, {
    headers: { Authorization: `Bearer ${token}`, "X-Porterchain-Portal": "merchant" },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw onboardingError(body, "Could not load onboarding status.");
  }
  return res.json();
}

export async function saveMerchantVertical(
  token: string,
  vertical: string,
  attribution?: Record<string, string>
): Promise<PortalOnboardingStatus> {
  const res = await fetch(`${publicEnv.porterchainApiUrl}/v1/auth/merchant/onboarding/vertical`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Porterchain-Portal": "merchant",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(
      attribution && Object.keys(attribution).length ? { vertical, attribution } : { vertical }
    ),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw onboardingError(body, "Could not save that business type.");
  }
  return res.json();
}

export async function saveMerchantCompanyFile(
  token: string,
  body: CompanyFileUpdate
): Promise<PortalOnboardingStatus> {
  const res = await fetch(`${publicEnv.porterchainApiUrl}/v1/auth/merchant/onboarding/profile`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Porterchain-Portal": "merchant",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    throw onboardingError(payload, "Could not save the company file.");
  }
  return res.json();
}

export const PENDING_MERCHANT_PATHS = ["/onboarding"] as const;

export function isPendingMerchantPath(pathname: string): boolean {
  return PENDING_MERCHANT_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

/** What the waiting seat is actually waiting on — the seat, or PorterChain (AY). */
export function onboardingWaitCopy(data: PortalOnboardingStatus): string {
  return waitCopy(data, merchantStatusLabel);
}

/** Only nag about the company file when it is genuinely incomplete and this seat cannot fix it. */
export function shouldAskOwnerForCompanyFile(data: PortalOnboardingStatus): boolean {
  return askOwnerForCompanyFile(data);
}

/** Where a teammate signs up. Invite email is not built yet, so the copy must carry the URL. */
export function merchantSignupUrl(signupUrl?: string | null): string {
  return signupUrl || `${publicEnv.siteUrl}/sign-up`;
}
