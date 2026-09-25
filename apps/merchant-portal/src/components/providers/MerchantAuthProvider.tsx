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
import { readImpersonationBearer } from "@porterchain/auth";
import { isClerkConfigured, useClerkDevApiBypass } from "@/lib/env";
import { getMerchantSession, type MerchantSession } from "@/lib/api";

const MERCHANT_ID_KEY = "pc_merchant_id";

export type MerchantAuthState = {
  isLoaded: boolean;
  isSignedIn: boolean;
  /** Active merchant id — sent as X-Merchant-Id (M-26). */
  orgId: string | undefined;
  modules: string[];
  role: string | undefined;
  session: MerchantSession | null;
  setOrgId: (merchantId: string) => void;
  refreshSession: () => Promise<void>;
  getApiToken: () => Promise<string>;
};

const MerchantAuthContext = createContext<MerchantAuthState | null>(null);

function readStoredMerchantId(): string | undefined {
  if (typeof window === "undefined") return undefined;
  try {
    return localStorage.getItem(MERCHANT_ID_KEY) || undefined;
  } catch {
    return undefined;
  }
}

function DevMerchantAuthProvider({ children }: { children: ReactNode }) {
  const [orgId, setOrgIdState] = useState<string | undefined>(undefined);
  const [session, setSession] = useState<MerchantSession | null>(null);
  const [sessionReady, setSessionReady] = useState(false);

  const refreshSession = useCallback(async (merchantId?: string) => {
    const s = await getMerchantSession("dev", merchantId ?? readStoredMerchantId());
    setSession(s);
    setOrgIdState(s.merchant_id);
    try {
      localStorage.setItem(MERCHANT_ID_KEY, s.merchant_id);
    } catch {
      /* ignore */
    }
  }, []);

  const setOrgId = useCallback(
    (merchantId: string) => {
      setOrgIdState(merchantId);
      try {
        localStorage.setItem(MERCHANT_ID_KEY, merchantId);
      } catch {
        /* ignore */
      }
      void refreshSession(merchantId).catch(() => {
        /* keep selected id */
      });
    },
    [refreshSession]
  );

  useEffect(() => {
    void (async () => {
      try {
        await refreshSession(readStoredMerchantId());
      } catch {
        setSession(null);
      } finally {
        setSessionReady(true);
      }
    })();
  }, [refreshSession]);

  const value = useMemo<MerchantAuthState>(
    () => ({
      isLoaded: sessionReady,
      isSignedIn: true,
      orgId,
      modules: session?.modules ?? [],
      role: session?.role,
      session,
      setOrgId,
      refreshSession,
      getApiToken: async () => "dev",
    }),
    [orgId, refreshSession, session, sessionReady, setOrgId]
  );
  return <MerchantAuthContext.Provider value={value}>{children}</MerchantAuthContext.Provider>;
}

function ClerkMerchantAuthProvider({ children }: { children: ReactNode }) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const devApiBypass = useClerkDevApiBypass();
  const [orgId, setOrgIdState] = useState<string | undefined>(undefined);
  const [session, setSession] = useState<MerchantSession | null>(null);
  const [sessionReady, setSessionReady] = useState(false);
  const [hasImpersonation, setHasImpersonation] = useState(false);
  const sessionRef = useRef(session);
  sessionRef.current = session;

  useEffect(() => {
    setHasImpersonation(Boolean(readImpersonationBearer()));
  }, []);

  const getApiToken = useCallback(async () => {
    const imp = readImpersonationBearer();
    if (imp) return imp;
    if (isSignedIn) {
      const token = await getToken();
      if (token) return token;
      throw new Error("Not authenticated");
    }
    if (devApiBypass) return "dev";
    throw new Error("Not authenticated");
  }, [devApiBypass, getToken, isSignedIn]);

  const refreshSession = useCallback(
    async (merchantId?: string) => {
      const token = await getApiToken();
      const s = await getMerchantSession(token, merchantId ?? readStoredMerchantId());
      setSession(s);
      setOrgIdState(s.merchant_id);
      try {
        localStorage.setItem(MERCHANT_ID_KEY, s.merchant_id);
      } catch {
        /* ignore */
      }
    },
    [getApiToken]
  );

  const setOrgId = useCallback(
    (merchantId: string) => {
      setOrgIdState(merchantId);
      try {
        localStorage.setItem(MERCHANT_ID_KEY, merchantId);
      } catch {
        /* ignore */
      }
      void refreshSession(merchantId).catch(() => {
        /* keep selected id */
      });
    },
    [refreshSession]
  );

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn && !devApiBypass && !hasImpersonation) {
      setSession(null);
      setSessionReady(true);
      return;
    }
    // Keep prior session painted while refreshing — blanking sessionReady flashes ModuleGate.
    if (!sessionRef.current) setSessionReady(false);
    void refreshSession()
      .catch(() => {
        setSession(null);
      })
      .finally(() => {
        setSessionReady(true);
      });
  }, [devApiBypass, hasImpersonation, isLoaded, isSignedIn, refreshSession]);

  const value = useMemo<MerchantAuthState>(
    () => ({
      isLoaded: isLoaded && sessionReady,
      isSignedIn: Boolean(isSignedIn) || hasImpersonation || (devApiBypass && !isSignedIn),
      orgId,
      modules: session?.modules ?? [],
      role: session?.role,
      session,
      setOrgId,
      refreshSession,
      getApiToken,
    }),
    [
      devApiBypass,
      getApiToken,
      hasImpersonation,
      isLoaded,
      isSignedIn,
      orgId,
      refreshSession,
      session,
      sessionReady,
      setOrgId,
    ]
  );

  return <MerchantAuthContext.Provider value={value}>{children}</MerchantAuthContext.Provider>;
}

export function MerchantAuthProvider({ children }: { children: ReactNode }) {
  if (useClerkDevApiBypass() || !isClerkConfigured()) {
    return <DevMerchantAuthProvider>{children}</DevMerchantAuthProvider>;
  }
  return <ClerkMerchantAuthProvider>{children}</ClerkMerchantAuthProvider>;
}

export function useMerchantAuth(): MerchantAuthState {
  const ctx = useContext(MerchantAuthContext);
  if (!ctx) {
    throw new Error("useMerchantAuth must be used within MerchantAuthProvider");
  }
  return ctx;
}
