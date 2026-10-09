/**
 * Shared hide rules for the Capacity Guide floating launcher.
 * Accepts locale-prefixed (`/en/business`) or stripped (`/business`) paths.
 */
export function isCapacityGuideFabHidden(pathname: string): boolean {
  const parts = pathname
    .replace(/^\/+|\/+$/g, "")
    .split("/")
    .filter(Boolean);
  const offset = parts[0] === "en" || parts[0] === "fr" ? 1 : 0;
  const rest = parts.slice(offset);
  // Home no longer embeds the chat inline (website Phase 1), so the launcher shows there too.
  if (rest.length === 0) return false;
  const head = rest[0];
  if (head === "login" || head === "sign-in" || head === "sign-up") return true;
  return false;
}

/** Space above the guide FAB so WhatsApp does not cover it (h-14 + gap). */
export const MOBILE_WHATSAPP_FAB_OFFSET_ABOVE_GUIDE =
  "max(5.75rem, calc(4.5rem + 1rem + env(safe-area-inset-bottom, 0px)))";

export const MOBILE_FAB_BOTTOM_DEFAULT =
  "max(1.25rem, calc(1rem + env(safe-area-inset-bottom, 0px)))";
