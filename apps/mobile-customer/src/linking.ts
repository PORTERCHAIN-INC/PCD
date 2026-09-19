import * as Linking from "expo-linking";

export type Screen = "sign-in" | "track";

export function screenFromUrl(url: string | null): { screen: Screen; tracking?: string } | null {
  if (!url) return null;
  const parsed = Linking.parse(url);
  const path = parsed.path ?? "";
  if (path.includes("track")) {
    const parts = path.split("/").filter(Boolean);
    const idx = parts.findIndex((part) => part === "track");
    const tracking = idx >= 0 ? parts[idx + 1] : undefined;
    return { screen: "track", tracking };
  }
  if (path.includes("login")) return { screen: "sign-in" };
  return null;
}
