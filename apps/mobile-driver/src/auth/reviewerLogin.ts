/**
 * G21 (doc 74 §3, A-APR-01/02/08): App Review sign-in. Interim path until Keycloak (L36) is
 * live: Clerk email + password only. If Clerk asks for any code or second factor we stop and
 * show an error instead of a code screen, so reviewers never see an OTP or CAPTCHA.
 * Flags (build-time, default OFF):
 *   EXPO_PUBLIC_REVIEWER_LOGIN_ENABLED=true   shows the email + password form
 *   EXPO_PUBLIC_APPLE_SIGN_IN_ENABLED=true    shows Sign in with Apple (needs Keycloak live)
 *   EXPO_PUBLIC_KEYCLOAK_URL / EXPO_PUBLIC_KEYCLOAK_REALM / EXPO_PUBLIC_KEYCLOAK_CLIENT_ID
 * No password is ever bundled: the reviewer types the one given in App Store Connect / Play Console.
 */

type Env = Record<string, string | undefined>;

// Expo inlines EXPO_PUBLIC_* only for literal `process.env.X` reads, so list them here.
const BUILD_ENV: Env = {
  EXPO_PUBLIC_REVIEWER_LOGIN_ENABLED: process.env.EXPO_PUBLIC_REVIEWER_LOGIN_ENABLED,
  EXPO_PUBLIC_APPLE_SIGN_IN_ENABLED: process.env.EXPO_PUBLIC_APPLE_SIGN_IN_ENABLED,
  EXPO_PUBLIC_KEYCLOAK_URL: process.env.EXPO_PUBLIC_KEYCLOAK_URL,
  EXPO_PUBLIC_KEYCLOAK_REALM: process.env.EXPO_PUBLIC_KEYCLOAK_REALM,
  EXPO_PUBLIC_KEYCLOAK_CLIENT_ID: process.env.EXPO_PUBLIC_KEYCLOAK_CLIENT_ID,
};

const on = (v: string | undefined) => (v ?? "").trim().toLowerCase() === "true";

export function reviewerLoginEnabled(env: Env = BUILD_ENV): boolean {
  return on(env.EXPO_PUBLIC_REVIEWER_LOGIN_ENABLED);
}

export type KeycloakConfig = { url: string; realm: string; clientId: string };

export function keycloakConfig(env: Env = BUILD_ENV): KeycloakConfig | null {
  const url = (env.EXPO_PUBLIC_KEYCLOAK_URL ?? "").trim().replace(/\/$/, "");
  const realm = (env.EXPO_PUBLIC_KEYCLOAK_REALM ?? "porterchain").trim();
  const clientId = (env.EXPO_PUBLIC_KEYCLOAK_CLIENT_ID ?? "").trim();
  return url && clientId ? { url, realm, clientId } : null;
}

/** Apple button shows only when flagged on AND Keycloak is configured (L36). */
export function appleSignInEnabled(env: Env = BUILD_ENV): boolean {
  return on(env.EXPO_PUBLIC_APPLE_SIGN_IN_ENABLED) && keycloakConfig(env) != null;
}

/** Keycloak authorize URL that jumps straight to the Apple IdP (kc_idp_hint=apple). */
export function appleAuthorizeUrl(kc: KeycloakConfig, redirectUri: string, state: string): string {
  const q = new URLSearchParams({
    client_id: kc.clientId,
    response_type: "code",
    scope: "openid email profile",
    redirect_uri: redirectUri,
    kc_idp_hint: "apple",
    state,
  });
  return `${kc.url}/realms/${encodeURIComponent(kc.realm)}/protocol/openid-connect/auth?${q}`;
}

export function validateCredentials(email: string, password: string): string | null {
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) return "Enter the review email address.";
  if (password.length < 8) return "Enter the review password.";
  return null;
}

type SignInResource = {
  create: (p: { identifier: string; password: string }) => Promise<{
    status: string | null;
    createdSessionId: string | null;
  }>;
};

/** Password-only sign-in. Throws `reviewer_needs_code` rather than ever asking for a code. */
export async function passwordSignIn(
  signIn: SignInResource,
  setActive: (p: { session: string }) => Promise<void>,
  email: string,
  password: string
): Promise<void> {
  const res = await signIn.create({ identifier: email.trim(), password });
  if (res.status !== "complete" || !res.createdSessionId) throw new Error("reviewer_needs_code");
  await setActive({ session: res.createdSessionId });
}

export function reviewerErrorCopy(code: string): string {
  if (code === "reviewer_needs_code")
    return "This account needs a code. Review accounts must be set to password only.";
  return "Email or password is wrong. Check the details in the review notes.";
}
