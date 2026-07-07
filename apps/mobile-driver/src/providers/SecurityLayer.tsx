import { useMemo, type ReactNode } from "react";
import {
  ClerkBridge,
  MobileSecurityProvider,
  readMobileSecurityEnv,
} from "@porterchain/mobile-security";
import { useAuthStore } from "../store/auth-store";
import { mobileEnv } from "../config/env";

export function SecurityLayer({ children }: { children: ReactNode }) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const clearSession = useAuthStore((s) => s.clearSession);
  const env = useMemo(
    () => ({
      ...readMobileSecurityEnv(),
      apiBaseUrl: mobileEnv.apiBaseUrl,
      clerkPublishableKey: mobileEnv.clerkPublishableKey,
      appKind: "driver" as const,
    }),
    []
  );

  return (
    <ClerkBridge env={env}>
      <MobileSecurityProvider
        appKind="driver"
        env={env}
        getAccessToken={() => accessToken}
        onSessionTimeout={() => void clearSession()}
      >
        {children}
      </MobileSecurityProvider>
    </ClerkBridge>
  );
}
