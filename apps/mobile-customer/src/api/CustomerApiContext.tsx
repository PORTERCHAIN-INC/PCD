import { createContext, useContext, useMemo, type ReactNode } from "react";
import { createCustomerApi, type CustomerApi } from "@porterchain/mobile-api";
import { createSecureApiClient, emitSecurityEvent } from "@porterchain/mobile-security";
import { mobileEnv } from "../config/env";
import { useAuthStore } from "../store/auth-store";

const CustomerApiContext = createContext<CustomerApi | null>(null);

export function CustomerApiProvider({ children }: { children: ReactNode }) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const clearSession = useAuthStore((s) => s.clearSession);

  const api = useMemo(
    () =>
      createCustomerApi(
        createSecureApiClient({
          baseUrl: mobileEnv.apiBaseUrl,
          appKind: "customer",
          getAccessToken: () => accessToken,
          onUnauthorized: () => {
            void emitSecurityEvent("logout");
            void clearSession();
          },
        })
      ),
    [accessToken, clearSession]
  );

  return <CustomerApiContext.Provider value={api}>{children}</CustomerApiContext.Provider>;
}

export function useCustomerApi() {
  const ctx = useContext(CustomerApiContext);
  if (!ctx) throw new Error("useCustomerApi must be used within CustomerApiProvider");
  return ctx;
}
