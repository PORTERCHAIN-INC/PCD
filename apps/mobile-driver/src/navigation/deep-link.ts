import type { NavigationContainerRef } from "@react-navigation/native";
import { parseDeepLink } from "@porterchain/mobile-notifications";
import type { RootStackParamList } from "../navigation/types";

type NavRef = NavigationContainerRef<RootStackParamList>;

export function handleDriverDeepLink(ref: NavRef, deepLink: string) {
  const parsed = parseDeepLink(deepLink, "porterchain-driver");
  const screen = parsed.screen ?? "";
  const id = parsed.params.id ?? parsed.params.orderId;

  if (screen === "jobs" && id) {
    ref.navigate("Main", {
      screen: "Jobs",
      params: { screen: "JobDetail", params: { orderId: id } },
    } as never);
    return;
  }

  if (screen === "navigation") {
    ref.navigate("Main", {
      screen: "Navigation",
      params: { screen: "Navigation", params: id ? { orderId: id } : undefined },
    } as never);
    return;
  }

  if (screen === "support") {
    ref.navigate("Main", {
      screen: "More",
      params: { screen: "Support" },
    } as never);
    return;
  }

  if (screen === "sos" || screen === "emergency") {
    ref.navigate("Main", {
      screen: "More",
      params: { screen: "Sos" },
    } as never);
    return;
  }

  if (screen === "notifications") {
    ref.navigate("Main", {
      screen: "More",
      params: { screen: "Notifications" },
    } as never);
  }
}
