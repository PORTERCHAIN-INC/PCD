/**
 * Every error the driver can see goes through humanError(): plain words, no stack traces,
 * no API codes. One table for auth, field and network errors.
 */

const NOT_PROVISIONED = "This account is not set up for the driver app. Call dispatch.";
const SESSION_EXPIRED = "Your session expired. Sign in again.";
const NO_GPS = "Can't read GPS. Turn on Location for PorterChain Driver in Settings.";

const COPY: Record<string, string> = {
  // auth
  missing_portal_permission: NOT_PROVISIONED,
  user_not_provisioned: NOT_PROVISIONED,
  driver_user_not_provisioned: NOT_PROVISIONED,
  driver_not_provisioned: NOT_PROVISIONED,
  driver_portal_access_denied: NOT_PROVISIONED,
  driver_auth_required: "Sign in to continue.",
  unauthorized: "Sign in to continue.",
  signed_out: "Sign in to continue.",
  invalid_driver_token: SESSION_EXPIRED,
  invalid_token: SESSION_EXPIRED,
  driver_suspended: "This driver account is suspended. Call dispatch.",
  driver_not_found: "No driver profile is linked to this sign-in. Call dispatch.",
  driver_not_active: "This driver account is not active yet. Call dispatch.",
  email_clerk_mismatch: "This email does not match your driver profile. Call dispatch.",
  clerk_email_required: "Add a verified email to your account, then try again.",
  clerk_email_unverified: "Verify your email, then try again.",
  sign_in_failed: "Sign-in failed. Try again.",
  // network
  network_unavailable: "No connection. Try again when you have signal.",
  network_timeout: "The server took too long. Try again.",
  porterchain_api_timeout: "The server took too long. Try again.",
  offline_queue_full: "Phone storage is full. Free up space, then try again.",
  // field
  location_unavailable: NO_GPS,
  location_ping_failed: NO_GPS,
  background_location_failed:
    "Background location is off. Dispatch only sees you while the app is open.",
  not_at_stop: "GPS says you are not at this stop yet. Get closer, then tap Arrived.",
  pretrip_required: "Finish the vehicle check first.",
  shift_required: "Go on duty first.",
  no_stop: "There is no active stop. Pull down to refresh.",
  no_job: "There is no job to act on. Pull down to refresh.",
  camera_permission_denied: "Camera is off. Allow camera access in Settings.",
  photo_too_large: "Photo too large. Take it again a little further away.",
  photo_encode_failed: "Could not save the photo. Take it again.",
  sequence_version_conflict: "Dispatch changed your route. Pull down to refresh.",
};

const SWITCH_ACCOUNT_CODES = [
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
];

/** True when the sign-in worked but this account cannot use the driver app: offer Sign out. */
export function needsAccountSwitch(detail: string | null | undefined): boolean {
  const key = (detail || "").trim();
  return Boolean(key) && SWITCH_ACCOUNT_CODES.some((code) => key.includes(code));
}

/** Silent outcomes the driver chose (cancelled camera etc.) — show nothing. */
export function isSilentError(detail: string | null | undefined): boolean {
  return detail === "photo_cancelled";
}

export function humanError(detail: string | null | undefined): string {
  const key = (detail || "").trim();
  if (!key) return "Something went wrong. Try again.";
  if (COPY[key]) return COPY[key];
  if (key.startsWith("driver_onboarding_blocked:"))
    return "Finish your setup on the driver portal first.";
  if (/kCLErrorDomain|getCurrentPositionAsync|Cannot obtain current location/i.test(key))
    return NO_GPS;
  for (const [code, copy] of Object.entries(COPY)) if (key.includes(code)) return copy;
  if (/^http_5\d\d$/.test(key)) return "PorterChain is having trouble. Try again in a minute.";
  if (/^http_4\d\d$/.test(key)) return "That didn't work. Pull down to refresh and try again.";
  // Server sentences (e.g. "Capture a photo first") pass through; bare codes get a generic line.
  if (/^[a-z0-9_.:-]+$/.test(key)) return "That didn't work. Try again or call dispatch.";
  return key;
}
