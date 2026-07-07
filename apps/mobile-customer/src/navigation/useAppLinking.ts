import { useEffect, type RefObject } from "react";
import * as Linking from "expo-linking";
import type { NavigationContainerRef } from "@react-navigation/native";
import type { RootStackParamList } from "./types";
import { handleCustomerDeepLink } from "./deep-link";

export function useAppLinking(
  navigationRef: RefObject<NavigationContainerRef<RootStackParamList> | null>,
  enabled: boolean
) {
  useEffect(() => {
    if (!enabled) return;

    const open = (url: string) => {
      if (!navigationRef.current?.isReady()) return;
      handleCustomerDeepLink(navigationRef.current, url);
    };

    void Linking.getInitialURL().then((url) => {
      if (url) open(url);
    });

    const sub = Linking.addEventListener("url", ({ url }) => open(url));
    return () => sub.remove();
  }, [enabled, navigationRef]);
}
