import { Linking, Platform } from "react-native";
import { getSettings } from "./settings";

type Dest = {
  navigationUrl?: string | null;
  lat?: number | null;
  lng?: number | null;
  address?: string | null;
};

/** Candidate deep links, best first. All free: the phone's own maps app does the routing. */
/** Deep link for the driver's chosen app (Settings → Navigation app). */
export function preferredLink(app: string, q: string, os: string): string | null {
  if (!q) return null;
  if (app === "waze")
    return /^-?\d/.test(q)
      ? `https://waze.com/ul?ll=${q}&navigate=yes`
      : `https://waze.com/ul?q=${q}&navigate=yes`;
  if (app === "google")
    return os === "android"
      ? `google.navigation:q=${q}&mode=d`
      : `comgooglemaps://?daddr=${q}&directionsmode=driving`;
  if (app === "apple" && os === "ios") return `maps://?daddr=${q}&dirflg=d`;
  return null;
}

export function navigationLinks(
  dest: Dest,
  os: string = Platform.OS,
  app: string = getSettings().nav_app
): string[] {
  const nav = dest.navigationUrl?.trim();
  const hasCoords = dest.lat != null && dest.lng != null;
  const q = hasCoords ? `${dest.lat},${dest.lng}` : encodeURIComponent(dest.address?.trim() ?? "");
  if (!nav && !q) return [];
  const links: string[] = [];
  const preferred = preferredLink(app, q, os);
  if (preferred) links.push(preferred);
  if (nav) links.push(nav);
  if (os === "android") {
    // Straight into Google Maps turn-by-turn; geo: is the any-app fallback.
    links.push(`google.navigation:q=${q}&mode=d`);
    links.push(hasCoords ? `geo:${q}?q=${q}` : `geo:0,0?q=${q}`);
  } else if (os === "ios") {
    links.push(`comgooglemaps://?daddr=${q}&directionsmode=driving`);
    links.push(`maps://?daddr=${q}&dirflg=d`);
  }
  return [...new Set(links)];
}

/**
 * One-tap navigate. Prefers the API's Valhalla/OSRM navigation_url, then Google Maps, then the
 * built-in maps app. Never calls a paid routing API (no Google Directions / Distance Matrix).
 */
export async function openTurnByTurn(dest: Dest): Promise<void> {
  const links = navigationLinks(dest);
  if (!links.length) throw new Error("No stop to navigate to");
  for (const url of links) {
    try {
      await Linking.openURL(url);
      return;
    } catch {
      /* app not installed: try the next one */
    }
  }
  throw new Error("No maps app available");
}
