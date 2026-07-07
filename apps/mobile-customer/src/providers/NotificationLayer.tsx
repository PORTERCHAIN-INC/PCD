import { useMemo, type ReactNode } from "react";
import {
  NotificationProvider,
  createCustomerNotificationAdapter,
} from "@porterchain/mobile-notifications";
import { useCustomerApi } from "../api/CustomerApiContext";
import { mobileEnv } from "../config/env";
import { handleCustomerDeepLink } from "../navigation/deep-link";
import { navigationRef } from "../navigation/navigation-ref";
import { useAuthStore } from "../store/auth-store";

export function NotificationLayer({ children }: { children: ReactNode }) {
  const api = useCustomerApi();
  const accessToken = useAuthStore((s) => s.accessToken);
  const adapter = useMemo(() => createCustomerNotificationAdapter(api), [api]);

  return (
    <NotificationProvider
      adapter={adapter}
      apiBaseUrl={mobileEnv.apiBaseUrl}
      getAccessToken={() => accessToken}
      appScheme="porterchain-customer"
      mode="customer"
      enabled={Boolean(accessToken)}
      onDeepLink={(link) => {
        if (navigationRef.isReady()) handleCustomerDeepLink(navigationRef, link);
      }}
    >
      {children}
    </NotificationProvider>
  );
}
