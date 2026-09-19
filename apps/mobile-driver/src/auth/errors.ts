/** Driver-facing auth copy — keep codes aligned with packages/auth authErrors. */

const COPY: Record<string, string> = {
  missing_portal_permission: "This account is not provisioned for the driver app.",
  porterchain_api_timeout: "Porterchain API did not respond. Check connectivity and try again.",
  driver_auth_required: "Sign in required.",
  invalid_driver_token: "Session expired. Sign in again.",
  driver_suspended: "This driver account is suspended. Contact operations.",
  driver_not_found: "No driver profile is linked to this sign-in.",
  driver_not_active: "This driver account is not active yet.",
  sign_in_failed: "Sign-in failed. Try again.",
  unauthorized: "Sign in required.",
};

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
    return "Could not complete sign-in. Try again or contact support.";
  }
  return key;
}
