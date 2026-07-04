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
  /** True once Porterchain API calls may proceed (Clerk session or dev bypass). */
  authReady: boolean;
  getApiToken: () => Promise<string>;
};

const AdminAuthContext = createContext<AdminAuthState | null>(null);

const TOKEN_CACHE_MS = 50_000;

function DevAdminAuthProvider({ children }: { children: ReactNode }) {
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
    if (devApiBypass) {
      return "dev";
    }

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

    if (process.env.NODE_ENV === "development") {
      return "dev";
    }
    throw new Error("Not authenticated");
  }, [devApiBypass, getToken]);

  useEffect(() => {
    if (devApiBypass) return;
    if (!isLoaded) return;
    if (!isSignedIn) {
      if (process.env.NODE_ENV === "development") {
        setJwtReady(true);
      }
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

  const authReady = devApiBypass
    ? isLoaded && (Boolean(isSignedIn) || process.env.NODE_ENV === "development")
    : jwtReady;

  const value = useMemo<AdminAuthState>(
    () => ({
      isLoaded,
      isSignedIn: Boolean(isSignedIn),
      authReady,
      getApiToken,
    }),
    [authReady, getApiToken, isLoaded, isSignedIn]
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
