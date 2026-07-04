import { useMemo, type ReactNode } from "react";
import { createApiClient, createCustomerApi } from "@porterchain/mobile-api";
import {
  ClerkBridge,
  MobileSecurityProvider,
  principalFromAuthMe,
  readMobileSecurityEnv,
} from "@porterchain/mobile-security";
import { useAuthStore } from "../store/auth-store";
import { mobileEnv } from "../config/env";

export function SecurityLayer({ children }: { children: ReactNode }) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const clearSession = useAuthStore((s) => s.clearSession);
  const env = useMemo(
    () => ({ ...readMobileSecurityEnv(), apiBaseUrl: mobileEnv.apiBaseUrl, appKind: "customer" as const }),
    []
  );

  return (
    <ClerkBridge env={env}>
      <MobileSecurityProvider
        appKind="customer"
        env={env}
        getAccessToken={() => accessToken}
        onSessionTimeout={() => void clearSession()}
        onLoadPrincipal={async (token) => {
          const api = createCustomerApi(
            createApiClient({ baseUrl: mobileEnv.apiBaseUrl, getAccessToken: () => token })
          );
          try {
            const me = await api.authMe();
            return principalFromAuthMe({
              user_id: me.user_id,
              roles: me.roles,
              permissions: me.permissions,
            });
          } catch {
            return null;
          }
        }}
      >
        {children}
      </MobileSecurityProvider>
    </ClerkBridge>
  );
}
