/**
 * Detect phone browsers (not tablets/desktop) where WhatsApp deep links
 * are the preferred live-chat surface (desktop uses the on-site Logistics line).
 */
export function isMobilePhoneBrowser(): boolean {
  if (typeof navigator === "undefined") return false;

  const ua = navigator.userAgent;
  if (/iPhone|iPod|Windows Phone/i.test(ua)) return true;
  // Android phones include "Mobile"; tablets usually do not.
  if (/Android/i.test(ua) && /Mobile/i.test(ua)) return true;
  if (/Mobi/i.test(ua) && !/iPad|Tablet|PlayBook/i.test(ua)) return true;
  return false;
}
