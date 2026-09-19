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

/** Open Apple Maps (iOS) or Google Maps (Android). GPS remains in Fleetbase. */
export async function openTurnByTurn(dest: Dest): Promise<void> {
  const nav = dest.navigationUrl?.trim();
  if (nav) {
    await Linking.openURL(nav);
    return;
  }

  const hasCoords = dest.lat != null && dest.lng != null;
  const query = hasCoords ? coords(dest.lat as number, dest.lng as number) : dest.address?.trim();
  if (!query) {
    throw new Error("No stop to navigate to");
  }
  const encoded = encodeURIComponent(query);
  const url =
    Platform.OS === "ios"
      ? `http://maps.apple.com/?daddr=${encoded}&dirflg=d`
      : `https://www.google.com/maps/dir/?api=1&destination=${encoded}&travelmode=driving`;
  await Linking.openURL(url);
}
