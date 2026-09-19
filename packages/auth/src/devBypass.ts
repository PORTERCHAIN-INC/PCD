/**
 * The one rule that decides whether a portal may skip Clerk (BJ).
 *
 * `NEXT_PUBLIC_CLERK_DEV_BYPASS=true` makes a portal skip the sign-in widget and
 * call the API with `Bearer dev`. That is a local convenience, and it must be
 * impossible in a shipped build — a leaked variable in Doppler or CI must not
 * turn a production portal into an open shell.
 *
 * `next build` sets `NODE_ENV=production`, so the compiler folds the check below
 * to a constant `false` in a shipped bundle — verified: `isDevelopmentBuild`
 * compiles to `return!1`. The variable can be set to anything at build or run
 * time and the bypass stays unreachable.
 *
 * No React or Next imports here: middleware runs on the Edge runtime and imports
 * this directly.
 */

/** True only in a development build. A production bundle can never return true. */
export function isDevelopmentBuild(): boolean {
  return process.env.NODE_ENV !== "production";
}

/**
 * True when this portal may skip Clerk and send `Bearer dev` to the API.
 *
 * Requires both a development build and the explicit opt-in, so it stays off by
 * default even locally.
 */
export function clerkDevBypassEnabled(): boolean {
  return isDevelopmentBuild() && process.env.NEXT_PUBLIC_CLERK_DEV_BYPASS === "true";
}

/**
 * True when the variable is set but the build refuses to honour it.
 *
 * Portals log this once at boot so a misconfigured deploy is visible in logs
 * instead of looking like a mysterious wall of 401s.
 */
export function clerkDevBypassIgnored(): boolean {
  return !isDevelopmentBuild() && process.env.NEXT_PUBLIC_CLERK_DEV_BYPASS === "true";
}
