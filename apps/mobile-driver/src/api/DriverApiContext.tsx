import { createContext, useContext, useMemo, type ReactNode } from "react";
import { createDriverApi, type DriverApi } from "@porterchain/mobile-api";
import { createSecureApiClient, emitSecurityEvent } from "@porterchain/mobile-security";
import { mobileEnv } from "../config/env";
import { useAuthStore } from "../store/auth-store";

const DriverApiContext = createContext<DriverApi | null>(null);

export function DriverApiProvider({ children }: { children: ReactNode }) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const refreshToken = useAuthStore((s) => s.refreshToken);
  const driverId = useAuthStore((s) => s.driverId);
  const email = useAuthStore((s) => s.email);
  const setSession = useAuthStore((s) => s.setSession);
  const clearSession = useAuthStore((s) => s.clearSession);

  const api = useMemo(
    () =>
      createDriverApi(
        createSecureApiClient({
          baseUrl: mobileEnv.apiBaseUrl,
          appKind: "driver",
          getAccessToken: () => accessToken,
          getRefreshToken: () => refreshToken,
          onSessionRefreshed: (token, nextRefresh) => {
            if (!driverId) return;
            void setSession({
              token,
              refreshToken: nextRefresh ?? refreshToken ?? "",
              driverId,
              email: email ?? "",
            });
          },
          onUnauthorized: () => {
            void emitSecurityEvent("logout");
            void clearSession();
          },
        })
      ),
    [accessToken, clearSession, driverId, email, refreshToken, setSession]
  );

  return <DriverApiContext.Provider value={api}>{children}</DriverApiContext.Provider>;
}

export function useDriverApi() {
  const ctx = useContext(DriverApiContext);
  if (!ctx) throw new Error("useDriverApi must be used within DriverApiProvider");
  return ctx;
}
