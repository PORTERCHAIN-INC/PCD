"use client";

import { AppAuthProvider } from "@porterchain/auth";
import { useAuth } from "@porterchain/auth/oidc/client";
import { authDevBypassEnabled } from "@porterchain/auth/devBypass";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { STAFF_COOKIE_TOKEN } from "@/lib/staff-session";
import { useHydrated } from "@/hooks/useHydrated";

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
  // The server never knows the browser session. If the client already has it on its first
  // render, queries start "loading" there but not in the SSR HTML -> React #418 (intermittent,
  // any page). Expose auth only after mount so SSR and first client paint always match.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const isLoaded = mounted && (dev || oidc.isLoaded);
  const isSignedIn = mounted && (dev || Boolean(oidc.isSignedIn));
  const authReady = isLoaded && isSignedIn;

  // Callers that fire before the session probe finishes wait for it instead of throwing an
  // unhandled "Not authenticated" (that crashed pages such as Unit economics on first load).
  const state = useRef({ isLoaded, isSignedIn });
  const waiters = useRef<Array<() => void>>([]);
  useEffect(() => {
    state.current = { isLoaded, isSignedIn };
    if (isLoaded) {
      const w = waiters.current;
      waiters.current = [];
      w.forEach((fn) => fn());
    }
  }, [isLoaded, isSignedIn]);

  const getApiToken = useCallback(async () => {
    if (dev) return "dev";
    if (!state.current.isLoaded) {
      await new Promise<void>((resolve) => {
        waiters.current.push(resolve);
        window.setTimeout(resolve, 15000);
      });
    }
    if (state.current.isSignedIn) return STAFF_COOKIE_TOKEN;
    throw new Error("Not authenticated");
  }, [dev]);

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
  // Report signed-out while this component hydrates, so late-streamed boundaries render exactly
  // what the server rendered (see useHydrated).
  const hydrated = useHydrated();
  const pre = useMemo(
    () => ({ ...ctx, isLoaded: false, isSignedIn: false, authReady: false }),
    [ctx]
  );
  return hydrated ? ctx : pre;
}
