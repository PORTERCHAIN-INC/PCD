import type { NavigationContainerRef } from "@react-navigation/native";
import { parseDeepLink } from "@porterchain/mobile-notifications";
import type { RootStackParamList } from "../navigation/types";

type NavRef = NavigationContainerRef<RootStackParamList>;

export function handleCustomerDeepLink(ref: NavRef, deepLink: string) {
  const parsed = parseDeepLink(deepLink, "porterchain-customer");
  const screen = parsed.screen ?? "";
  const id = parsed.params.id ?? parsed.params.trackingNumber ?? parsed.params.orderId;

  if (screen === "tracking" && id) {
    ref.navigate("Main", {
      screen: "Tracking",
      params: { screen: "LiveMap", params: { trackingNumber: id } },
    } as never);
    return;
  }

  if (screen === "bookings" || screen === "orders") {
    ref.navigate("Main", {
      screen: "Bookings",
      params: { screen: "Bookings" },
    } as never);
    return;
  }

  if (screen === "support") {
    ref.navigate("Main", {
      screen: "Profile",
      params: { screen: "Support" },
    } as never);
    return;
  }

  if (screen === "claims") {
    ref.navigate("Main", {
      screen: "Profile",
      params: { screen: "Claims" },
    } as never);
    return;
  }

  if (screen === "notifications") {
    ref.navigate("Main", {
      screen: "Notifications",
      params: { screen: "Notifications" },
    } as never);
  }
}
