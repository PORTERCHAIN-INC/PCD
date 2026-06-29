"use client";

import { createContext, useCallback, useContext, useMemo, type ReactNode } from "react";
import { useAuth } from "@clerk/nextjs";
import { isClerkConfigured } from "@/lib/env";

const DEV_ORG = "dev_merchant_org";

export type MerchantAuthState = {
  isLoaded: boolean;
  isSignedIn: boolean;
  orgId: string | undefined;
  getApiToken: () => Promise<string>;
};

const MerchantAuthContext = createContext<MerchantAuthState | null>(null);

function DevMerchantAuthProvider({ children }: { children: ReactNode }) {
  const value = useMemo<MerchantAuthState>(
    () => ({
      isLoaded: true,
      isSignedIn: true,
      orgId: DEV_ORG,
      getApiToken: async () => "dev",
    }),
    []
  );
  return <MerchantAuthContext.Provider value={value}>{children}</MerchantAuthContext.Provider>;
}

function ClerkMerchantAuthProvider({ children }: { children: ReactNode }) {
  const { getToken, isLoaded, isSignedIn, orgId } = useAuth();

  const resolvedOrgId = useMemo(() => {
    if (orgId) return orgId;
    if (process.env.NODE_ENV === "development") return DEV_ORG;
    return undefined;
  }, [orgId]);

  const getApiToken = useCallback(async () => {
    const token = await getToken();
    if (token) return token;
    if (process.env.NODE_ENV === "development") return "dev";
    throw new Error("Not authenticated");
  }, [getToken]);

  const value = useMemo<MerchantAuthState>(
    () => ({
      isLoaded,
      isSignedIn: Boolean(isSignedIn),
      orgId: resolvedOrgId,
      getApiToken,
    }),
    [getApiToken, isLoaded, isSignedIn, resolvedOrgId]
  );

  return <MerchantAuthContext.Provider value={value}>{children}</MerchantAuthContext.Provider>;
}

export function MerchantAuthProvider({ children }: { children: ReactNode }) {
  if (isClerkConfigured()) {
    return <ClerkMerchantAuthProvider>{children}</ClerkMerchantAuthProvider>;
  }
  return <DevMerchantAuthProvider>{children}</DevMerchantAuthProvider>;
}

export function useMerchantAuth(): MerchantAuthState {
  const ctx = useContext(MerchantAuthContext);
  if (!ctx) {
    throw new Error("useMerchantAuth must be used within MerchantAuthProvider");
  }
  return ctx;
}
