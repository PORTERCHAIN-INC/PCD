export type OnboardingStepId =
  | "clerk_account"
  | "admin_approval"
  | "license_verified"
  | "insurance_verified"
  | "vehicle_verified"
  | "background_check"
  | "documents_uploaded";

export interface DriverOnboardingStep {
  id: OnboardingStepId | string;
  label: string;
  description: string;
  complete: boolean;
  status: string;
  missing?: string[];
  reason?: string | null;
}

export interface DriverOnboardingStatus {
  ready: boolean;
  blockers: string[];
  status: string;
  clerk_linked: boolean;
  steps: DriverOnboardingStep[];
  pending_documents: number;
  can_access_portal: boolean;
}

export async function fetchDriverOnboarding(): Promise<DriverOnboardingStatus> {
  const res = await fetch("/api/driver/v1/onboarding", { credentials: "include" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "onboarding_fetch_failed" }));
    throw new Error(err.detail || "onboarding_fetch_failed");
  }
  return res.json();
}

/** Routes accessible before full onboarding is complete. */
export const PENDING_DRIVER_PATHS = ["/onboarding", "/profile"] as const;

export function isPendingDriverPath(pathname: string): boolean {
  return PENDING_DRIVER_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}
