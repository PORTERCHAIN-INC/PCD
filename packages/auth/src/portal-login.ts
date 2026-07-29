/**
 * Platform login helpers for portal apps.
 */

/** Canonical Platform Clerk entry (website). Prefer `/login`; `/sign-in` redirects there. */
export function platformLoginUrl(websiteBaseUrl: string): string {
  return `${websiteBaseUrl.replace(/\/$/, "")}/login`;
}
