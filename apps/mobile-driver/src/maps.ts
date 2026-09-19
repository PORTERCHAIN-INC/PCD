import { Linking, Platform } from "react-native";

type Dest = {
  navigationUrl?: string | null;
  lat?: number | null;
  lng?: number | null;
  address?: string | null;
};

function coords(lat: number, lng: number): string {
  return `${lat},${lng}`;
}

/**
 * Prefer Valhalla/OSRM navigation_url from the API.
 * Fallback opens the native maps app for turn-by-turn UI only — never Google Distance Matrix.
 */
export async function openTurnByTurn(dest: Dest): Promise<void> {
  const nav = dest.navigationUrl?.trim();
  if (nav) {
    await Linking.openURL(nav);
    return;
  }

  const hasCoords = dest.lat != null && dest.lng != null;
  if (hasCoords) {
    const lat = dest.lat as number;
    const lng = dest.lng as number;
    const url =
      Platform.OS === "ios"
        ? `http://maps.apple.com/?daddr=${coords(lat, lng)}&dirflg=d`
        : `geo:${lat},${lng}?q=${lat},${lng}`;
    await Linking.openURL(url);
    return;
  }

  const address = dest.address?.trim();
  if (!address) {
    throw new Error("No stop to navigate to");
  }
  const encoded = encodeURIComponent(address);
  const url =
    Platform.OS === "ios"
      ? `http://maps.apple.com/?daddr=${encoded}&dirflg=d`
      : `geo:0,0?q=${encoded}`;
  await Linking.openURL(url);
}
