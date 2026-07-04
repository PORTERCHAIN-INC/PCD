import { useMemo, type ReactNode } from "react";
import {
  NotificationProvider,
  createDriverNotificationAdapter,
} from "@porterchain/mobile-notifications";
import { useDriverApi } from "../api/DriverApiContext";
import { mobileEnv } from "../config/env";
import { handleDriverDeepLink } from "../navigation/deep-link";
import { navigationRef } from "../navigation/navigation-ref";
import { useAuthStore } from "../store/auth-store";

export function NotificationLayer({ children }: { children: ReactNode }) {
  const api = useDriverApi();
  const accessToken = useAuthStore((s) => s.accessToken);
  const adapter = useMemo(() => createDriverNotificationAdapter(api), [api]);

  return (
    <NotificationProvider
      adapter={adapter}
      apiBaseUrl={mobileEnv.apiBaseUrl}
      getAccessToken={() => accessToken}
      appScheme="porterchain-driver"
      mode="driver"
      enabled={Boolean(accessToken)}
      onDeepLink={(link) => {
        if (navigationRef.isReady()) handleDriverDeepLink(navigationRef, link);
      }}
    >
      {children}
    </NotificationProvider>
  );
}
