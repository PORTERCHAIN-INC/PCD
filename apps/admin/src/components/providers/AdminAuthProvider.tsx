"use client";

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
import { useAuth } from "@clerk/nextjs";
import { isClerkConfigured, useClerkDevApiBypass } from "@/lib/env";

export type AdminAuthState = {
  isLoaded: boolean;
  isSignedIn: boolean;
  /** True once Porterchain API calls may proceed (Clerk session or explicit local bypass). */
  authReady: boolean;
  getApiToken: () => Promise<string>;
};

const AdminAuthContext = createContext<AdminAuthState | null>(null);

const TOKEN_CACHE_MS = 50_000;

function DevAdminAuthProvider({ children }: { children: ReactNode }) {
  // Only used when Clerk publishable key is missing — local shell without Clerk.
  const value = useMemo<AdminAuthState>(
    () => ({
      isLoaded: true,
      isSignedIn: true,
      authReady: true,
      getApiToken: async () => "dev",
    }),
    []
  );
  return <AdminAuthContext.Provider value={value}>{children}</AdminAuthContext.Provider>;
}

function ClerkAdminAuthProvider({ children }: { children: ReactNode }) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const devApiBypass = useClerkDevApiBypass();
  const tokenCache = useRef<{ token: string; at: number } | null>(null);
  const [jwtReady, setJwtReady] = useState(false);

  const getApiToken = useCallback(async () => {
    // Prefer the real Clerk JWT whenever a session exists. DEV_BYPASS Bearer `dev`
    // is only for unsigned local shells — never override a signed-in user.
    if (isSignedIn) {
      const cached = tokenCache.current;
      if (cached && Date.now() - cached.at < TOKEN_CACHE_MS) {
        return cached.token;
      }

      for (let attempt = 0; attempt < 4; attempt += 1) {
        const token = await getToken();
        if (token) {
          tokenCache.current = { token, at: Date.now() };
          return token;
        }
        if (attempt < 3) {
          await new Promise((resolve) => setTimeout(resolve, 150 * (attempt + 1)));
        }
      }
      throw new Error("Not authenticated");
    }

    if (devApiBypass) {
      return "dev";
    }

    throw new Error("Not authenticated");
  }, [devApiBypass, getToken, isSignedIn]);

  useEffect(() => {
    if (!isLoaded) {
      setJwtReady(false);
      return;
    }
    if (!isSignedIn) {
      tokenCache.current = null;
      setJwtReady(devApiBypass);
      return;
    }
    let cancelled = false;
    void getApiToken()
      .then(() => {
        if (!cancelled) setJwtReady(true);
      })
      .catch(() => {
        if (!cancelled) setJwtReady(false);
      });
    return () => {
      cancelled = true;
    };
  }, [devApiBypass, getApiToken, isLoaded, isSignedIn]);

  const authReady = isSignedIn ? jwtReady : Boolean(devApiBypass && isLoaded);

  const value = useMemo<AdminAuthState>(
    () => ({
      isLoaded,
      isSignedIn: Boolean(isSignedIn) || (devApiBypass && !isSignedIn),
      authReady,
      getApiToken,
    }),
    [authReady, devApiBypass, getApiToken, isLoaded, isSignedIn]
  );

  return <AdminAuthContext.Provider value={value}>{children}</AdminAuthContext.Provider>;
}

export function AdminAuthProvider({ children }: { children: ReactNode }) {
  if (isClerkConfigured()) {
    return <ClerkAdminAuthProvider>{children}</ClerkAdminAuthProvider>;
  }
  return <DevAdminAuthProvider>{children}</DevAdminAuthProvider>;
}

export function useAdminAuth(): AdminAuthState {
  const ctx = useContext(AdminAuthContext);
  if (!ctx) {
    throw new Error("useAdminAuth must be used within AdminAuthProvider");
  }
  return ctx;
}
