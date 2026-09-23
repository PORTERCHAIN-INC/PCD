/** Driver-facing auth copy — keep codes aligned with packages/auth authErrors. */

const COPY: Record<string, string> = {
  missing_portal_permission: "This account is not provisioned for the driver app.",
  user_not_provisioned: "This account is not provisioned for the driver app.",
  driver_user_not_provisioned: "This account is not provisioned for the driver app.",
  driver_not_provisioned: "This account is not provisioned for the driver app.",
  driver_portal_access_denied: "This account is not provisioned for the driver app.",
  porterchain_api_timeout: "Porterchain API did not respond. Check connectivity and try again.",
  driver_auth_required: "Sign in required.",
  invalid_driver_token: "Session expired. Sign in again.",
  invalid_token: "Session expired. Sign in again.",
  driver_suspended: "This driver account is suspended. Contact operations.",
  driver_not_found: "No driver profile is linked to this sign-in.",
  driver_not_active: "This driver account is not active yet.",
  email_clerk_mismatch: "This Clerk email does not match the driver profile. Contact operations.",
  clerk_email_required: "Add a verified email on this Clerk account, then try again.",
  clerk_email_unverified: "Verify your Clerk email, then try again.",
  sign_in_failed: "Sign-in failed. Try again.",
  unauthorized: "Sign in required.",
};

const SWITCH_ACCOUNT_CODES = new Set([
  "missing_portal_permission",
  "user_not_provisioned",
  "driver_user_not_provisioned",
  "driver_not_provisioned",
  "driver_portal_access_denied",
  "driver_not_found",
  "driver_not_active",
  "driver_suspended",
  "email_clerk_mismatch",
  "clerk_email_required",
  "clerk_email_unverified",
]);

/** True when the Clerk session is live but cannot enter the driver app — offer Sign out. */
export function needsAccountSwitch(detail: string | null | undefined): boolean {
  const key = (detail || "").trim();
  if (!key) return false;
  if (SWITCH_ACCOUNT_CODES.has(key)) return true;
  for (const code of SWITCH_ACCOUNT_CODES) {
    if (key.includes(code)) return true;
  }
  return /not provisioned for the driver app/i.test(key);
}

export function humanDriverError(detail: string | null | undefined): string {
  const key = (detail || "").trim();
  if (!key) return "Something went wrong. Try again.";
  if (COPY[key]) return COPY[key];
  for (const [code, copy] of Object.entries(COPY)) {
    if (key === code || key.includes(code)) return copy;
  }
  if (key === "Sign in required" || key.startsWith("API unreachable")) return key;
  if (key.startsWith("Sign-in failed")) return key;
  if (/^[a-z0-9_.]+$/.test(key) && key.includes("_")) {
    return `Could not complete sign-in (${key}). Try again or contact support.`;
  }
  return key;
}
