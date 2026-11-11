/**
 * Human copy for auth / portal gate failures — shared by admin, driver portal, mobile.
 * Keep codes stable; map only what callers surface today.
 */

const AUTH_ERROR_COPY: Record<string, string> = {
  missing_portal_permission: "This account is not provisioned for this portal.",
  porterchain_api_timeout: "Porterchain API did not respond. Check the API and try again.",
  db_unavailable: "Porterchain is busy right now. Wait a few seconds and try again.",
  missing_token: "Sign in required.",
  missing_bearer_token: "Sign in required.",
  staff_session_invalid: "Your staff session expired. Sign in again.",
  staff_auth_rate_limited: "Too many sign-in attempts. Wait a minute and try again.",
  staff_auth_rate_unavailable: "Sign-in temporarily unavailable. Try again shortly.",
  passkey_login_failed: "Passkey sign-in failed. Try the email activate link.",
  enrollment_invalid_or_expired: "This link expired or was already used. Request a new one.",
  driver_auth_required: "Sign in required.",
  invalid_driver_token: "Driver session expired. Sign in again.",
  driver_suspended: "This driver account is suspended. Contact operations.",
  driver_not_found: "No driver profile is linked to this sign-in.",
  driver_not_active: "This driver account is not active yet.",
  unauthorized: "Sign in required.",
  sign_in_failed: "Sign-in failed. Try again.",
  login_failed: "Sign-in failed. Try again.",
  login_request_failed: "Could not send the activate link. Try again.",
  local_super_admin_unavailable: "Local Super Admin is only available in development.",
  passkey_options_failed: "Passkey sign-in is unavailable. Try the email link.",
  email_required: "Enter your email to continue.",
  staff_step_up_required: "Confirm with your passkey before continuing.",
  // L212: signed in with an account that belongs to another portal.
  admin_user_not_found:
    "This account does not have staff access. Sign out and use your staff account.",
  driver_user_not_provisioned:
    "This account is not a driver account. Sign out and use the email your driver invitation was sent to.",
  merchant_user_not_found:
    "This account is not linked to a business. Sign out and use your business account.",
  "identity_conflict:idp_user_is_driver":
    "This is a driver account. Drivers sign in on the Driver portal. Sign out and use your business account.",
  "identity_conflict:idp_user_is_admin":
    "This is a staff account. Staff sign in on the Admin portal. Sign out and use your business account.",
  "identity_conflict:idp_user_is_merchant":
    "This is a business account. Sign out and use the right account for this portal.",
  idp_user_deactivated: "This account is deactivated. Contact PorterChain support.",
  account_suspended: "This account is suspended. Contact PorterChain support.",
};

/** L212: codes meaning "valid sign-in, wrong portal" — shown as Access denied, not Session error. */
const WRONG_PORTAL = new Set([
  "missing_portal_permission",
  "admin_user_not_found",
  "driver_user_not_provisioned",
  "merchant_user_not_found",
  "identity_conflict:idp_user_is_driver",
  "identity_conflict:idp_user_is_admin",
  "identity_conflict:idp_user_is_merchant",
]);

const BLOCKED = new Set(["driver_suspended", "idp_user_deactivated", "account_suspended"]);

/** L222: suspended / deactivated accounts get an "Account unavailable" title, not "Session error". */
export function isBlockedAccountError(detail: string | null | undefined): boolean {
  return BLOCKED.has((detail || "").trim());
}

export function isWrongPortalError(detail: string | null | undefined): boolean {
  return WRONG_PORTAL.has((detail || "").trim());
}

/** Map a machine detail / Error.message to operator-facing copy. */
export function humanAuthError(detail: string | null | undefined, fallback?: string): string {
  const key = (detail || "").trim();
  if (!key) return fallback || "Something went wrong. Try again.";
  if (AUTH_ERROR_COPY[key]) return AUTH_ERROR_COPY[key];
  // Nested FastAPI-style or prefixed messages
  for (const [code, copy] of Object.entries(AUTH_ERROR_COPY)) {
    if (key === code || key.endsWith(code) || key.includes(code)) return copy;
  }
  if (fallback) return fallback;
  // Avoid dumping raw snake_case at drivers when we can soften.
  if (/^[a-z0-9_.]+$/.test(key) && key.includes("_")) {
    return "Could not complete sign-in. Try again or contact support.";
  }
  return key;
}
