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

export async function fetchCustomerOnboarding(token: string): Promise<PortalOnboardingStatus> {
  const api = (process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ?? "http://localhost:8001").replace(
    /\/$/,
    ""
  );
  const res = await fetch(`${api}/v1/auth/customer/onboarding`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "onboarding_fetch_failed");
  }
  return res.json();
}

export const PENDING_CUSTOMER_PATHS = ["/onboarding"] as const;

export function isPendingCustomerPath(pathname: string): boolean {
  return PENDING_CUSTOMER_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}
