"use client";

import { useInactivityTimeout } from "@porterchain/auth";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { publicEnv } from "@/lib/env";
import {
  clearStaffSession,
  probeStaffCookie,
  STAFF_COOKIE_TOKEN,
  STAFF_AUTH_EVENT,
} from "@/lib/staff-session";

export type AdminAuthState = {
  isLoaded: boolean;
  isSignedIn: boolean;
  /** True once Porterchain API calls may proceed (Staff IdP cookie). */
  authReady: boolean;
  getApiToken: () => Promise<string>;
};

const AdminAuthContext = createContext<AdminAuthState | null>(null);

/**
 * Staff IdP auth — HttpOnly cookie via BFF.
 * Development uses the same path after Local Super Admin mints a real session.
 */
export function AdminAuthProvider({ children }: { children: ReactNode }) {
  const [cookieReady, setCookieReady] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const refreshCookie = useCallback(async () => {
    const ok = await probeStaffCookie();
    setCookieReady(ok);
    setLoaded(true);
  }, []);

  useEffect(() => {
    void refreshCookie();
  }, [refreshCookie]);

  useEffect(() => {
    const onAuth = () => {
      void refreshCookie();
    };
    window.addEventListener(STAFF_AUTH_EVENT, onAuth);
    return () => window.removeEventListener(STAFF_AUTH_EVENT, onAuth);
  }, [refreshCookie]);

  const getApiToken = useCallback(async () => {
    const ok = await probeStaffCookie();
    if (ok) return STAFF_COOKIE_TOKEN;
    throw new Error("Not authenticated");
  }, []);

  const isSignedIn = cookieReady;
  const authReady = loaded && isSignedIn;

  useEffect(() => {
    if (!authReady || typeof window === "undefined") return;
    const key = "pc_admin_push_registered_v1";
    try {
      if (window.localStorage.getItem(key) === "1") return;
    } catch {
      /* private mode */
    }
    let cancelled = false;
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
    return () => {
      cancelled = true;
    };
  }, [authReady, getApiToken]);

  useEffect(() => {
    if (!authReady || typeof window === "undefined") return;
    let unsub: (() => void) | null = null;
    let cancelled = false;
    void (async () => {
      try {
        const { attachForegroundMessaging } = await import("@/lib/firebase-messaging");
        const stop = await attachForegroundMessaging((msg) => {
          if (typeof Notification === "undefined" || Notification.permission !== "granted") return;
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
        if (cancelled) {
          stop?.();
          return;
        }
        unsub = stop;
      } catch {
        /* FCM unsupported */
      }
    })();
    return () => {
      cancelled = true;
      unsub?.();
    };
  }, [authReady]);

  const onIdleTimeout = useCallback(async () => {
    await clearStaffSession(publicEnv.porterchainApiUrl);
    window.location.assign("/sign-in?reason=idle");
  }, []);

  useInactivityTimeout({
    enabled: loaded && cookieReady,
    onTimeout: onIdleTimeout,
  });

  const value = useMemo<AdminAuthState>(
    () => ({
      isLoaded: loaded,
      isSignedIn,
      authReady,
      getApiToken,
    }),
    [authReady, getApiToken, isSignedIn, loaded]
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
