"use client";

import { createContext, useCallback, useContext, useMemo, type ReactNode } from "react";
import { useAuth } from "@clerk/nextjs";
import { isClerkConfigured } from "@/lib/env";

export type AdminAuthState = {
  isLoaded: boolean;
  isSignedIn: boolean;
  getApiToken: () => Promise<string>;
};

const AdminAuthContext = createContext<AdminAuthState | null>(null);

function DevAdminAuthProvider({ children }: { children: ReactNode }) {
  const value = useMemo<AdminAuthState>(
    () => ({
      isLoaded: true,
      isSignedIn: true,
      getApiToken: async () => "dev",
    }),
    []
  );
  return <AdminAuthContext.Provider value={value}>{children}</AdminAuthContext.Provider>;
}

function ClerkAdminAuthProvider({ children }: { children: ReactNode }) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const getApiToken = useCallback(async () => {
    const token = await getToken();
    if (token) return token;
    if (process.env.NODE_ENV === "development") return "dev";
    throw new Error("Not authenticated");
  }, [getToken]);

  const value = useMemo<AdminAuthState>(
    () => ({
      isLoaded,
      isSignedIn: Boolean(isSignedIn),
      getApiToken,
    }),
    [getApiToken, isLoaded, isSignedIn]
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
