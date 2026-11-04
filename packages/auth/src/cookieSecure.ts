/** Secure cookie flag: AUTH_COOKIE_SECURE=true|false overrides; otherwise on in production only. */
export function cookieSecure(env: NodeJS.ProcessEnv = process.env): boolean {
  return env.AUTH_COOKIE_SECURE
    ? env.AUTH_COOKIE_SECURE !== "false"
    : env.NODE_ENV === "production";
}
