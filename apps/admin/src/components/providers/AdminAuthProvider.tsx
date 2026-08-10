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
import { publicEnv, useClerkDevApiBypass } from "@/lib/env";
import { clearStaffSession, getStaffBearer } from "@/lib/staff-session";

export type AdminAuthState = {
  isLoaded: boolean;
  isSignedIn: boolean;
  /** True once Porterchain API calls may proceed (staff session or local bypass). */
  authReady: boolean;
  getApiToken: () => Promise<string>;
};

const AdminAuthContext = createContext<AdminAuthState | null>(null);

/** Staff IdP auth only — Clerk removed from admin (canvas Phase 5). */
export function AdminAuthProvider({ children }: { children: ReactNode }) {
  const devApiBypass = useClerkDevApiBypass();
  const [staffBearer, setStaffBearerState] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setStaffBearerState(getStaffBearer());
    setLoaded(true);
    const onStorage = () => setStaffBearerState(getStaffBearer());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  // Re-read after activate-staff sets sessionStorage in same tab.
  useEffect(() => {
    if (!loaded) return;
    const id = window.setInterval(() => {
      const next = getStaffBearer();
      setStaffBearerState((prev) => (prev === next ? prev : next));
    }, 1500);
    return () => window.clearInterval(id);
  }, [loaded]);

  const getApiToken = useCallback(async () => {
    const bearer = getStaffBearer();
    if (bearer) return bearer;
    if (devApiBypass) return "dev";
    throw new Error("Not authenticated");
  }, [devApiBypass]);

  const staffReady = Boolean(staffBearer);
  const isSignedIn = staffReady || devApiBypass;
  const authReady = loaded && isSignedIn;

  const onIdleTimeout = useCallback(async () => {
    await clearStaffSession(publicEnv.porterchainApiUrl);
    window.location.assign("/sign-in?reason=idle");
  }, []);

  // Real staff sessions only — do not idle-logout pure local API bypass.
  useInactivityTimeout({
    enabled: loaded && staffReady,
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
