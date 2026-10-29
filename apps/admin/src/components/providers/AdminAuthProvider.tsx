"use client";

import { AppAuthProvider } from "@porterchain/auth";
import { useAuth } from "@porterchain/auth/oidc/client";
import { authDevBypassEnabled } from "@porterchain/auth/devBypass";
import { createContext, useCallback, useContext, useEffect, useMemo, type ReactNode } from "react";
import { STAFF_COOKIE_TOKEN } from "@/lib/staff-session";

export type AdminAuthState = {
  isLoaded: boolean;
  isSignedIn: boolean;
  /** True once Porterchain API calls may proceed. */
  authReady: boolean;
  getApiToken: () => Promise<string>;
};

const AdminAuthContext = createContext<AdminAuthState | null>(null);

/**
 * Staff auth = Keycloak `pc-admin` (password + TOTP for admin tiers). The session is HttpOnly
 * cookies; the BFF attaches the access token, so callers pass the STAFF_COOKIE_TOKEN sentinel.
 * Local dev bypass uses API Bearer `dev`.
 */
export function AdminAuthProvider({ children }: { children: ReactNode }) {
  if (authDevBypassEnabled()) {
    return <AdminAuthInner dev>{children}</AdminAuthInner>;
  }
  return (
    <AppAuthProvider>
      <AdminAuthInner>{children}</AdminAuthInner>
    </AppAuthProvider>
  );
}

function AdminAuthInner({ children, dev = false }: { children: ReactNode; dev?: boolean }) {
  const oidc = useAuth();
  const isLoaded = dev || oidc.isLoaded;
  const isSignedIn = dev || Boolean(oidc.isSignedIn);
  const authReady = isLoaded && isSignedIn;

  const getApiToken = useCallback(async () => {
    if (dev) return "dev";
    if (isSignedIn) return STAFF_COOKIE_TOKEN;
    throw new Error("Not authenticated");
  }, [dev, isSignedIn]);

  useEffect(() => {
    if (!authReady || typeof window === "undefined") return;
    const key = "pc_admin_push_registered_v1";
    try {
      if (window.localStorage.getItem(key) === "1") return;
    } catch {
      /* private mode */
    }
    let cancelled = false;
    const run = () => {
      if (cancelled) return;
      void (async () => {
        try {
          const { registerBrowserPush } = await import("@/lib/web-push");
          const ok = await registerBrowserPush(getApiToken);
          if (!cancelled && ok) {
            try {
              window.localStorage.setItem(key, "1");
            } catch {
              /* ignore */
            }
          }
        } catch {
          /* permission denied / FCM unavailable — soft fail */
        }
      })();
    };
    const id = window.setTimeout(run, 2500);
    return () => {
      cancelled = true;
      window.clearTimeout(id);
    };
  }, [authReady, getApiToken]);

  useEffect(() => {
    if (!authReady || typeof window === "undefined") return;
    let unsub: (() => void) | null = null;
    let cancelled = false;
    const id = window.setTimeout(() => {
      void (async () => {
        try {
          const { attachForegroundMessaging } = await import("@porterchain/web-push/messaging");
          const stop = await attachForegroundMessaging((msg) => {
            if (typeof Notification === "undefined" || Notification.permission !== "granted")
              return;
            const urgent = msg.priority === "critical" || msg.priority === "high";
            try {
              new Notification(msg.title, {
                body: msg.body,
                tag: msg.tag,
                requireInteraction: urgent,
                silent: false,
              });
            } catch {
              /* Notification constructor may fail in some browsers */
            }
          });
          if (cancelled) stop?.();
          else unsub = stop;
        } catch {
          /* FCM unsupported */
        }
      })();
    }, 3000);
    return () => {
      cancelled = true;
      unsub?.();
      window.clearTimeout(id);
    };
  }, [authReady]);

  const value = useMemo<AdminAuthState>(
    () => ({ isLoaded, isSignedIn, authReady, getApiToken }),
    [authReady, getApiToken, isSignedIn, isLoaded]
  );
  return <AdminAuthContext.Provider value={value}>{children}</AdminAuthContext.Provider>;
}

export function useAdminAuth(): AdminAuthState {
  const ctx = useContext(AdminAuthContext);
  if (!ctx) {
    throw new Error("useAdminAuth must be used within AdminAuthProvider");
  }
  return ctx;
}
