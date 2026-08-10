"use client";

import { useEffect, useState } from "react";
import {
  canAccessPortal,
  fetchSessionContext,
  type PorterchainPortal,
  type SessionContext,
} from "./session-context";

export type PortalOnboardingSnapshot = {
  ready: boolean;
};

export type UsePortalSessionGateOptions = {
  portal: PorterchainPortal;
  apiUrl: string;
  isLoaded: boolean;
  isSignedIn: boolean;
  getToken: () => Promise<string | null>;
  /** When true, skip session fetch (e.g. already on /onboarding). */
  skipCheck?: boolean;
  /** Optional onboarding probe before session-context (merchant/customer). */
  fetchOnboarding?: (token: string) => Promise<PortalOnboardingSnapshot>;
  onSession?: (ctx: SessionContext) => void;
  onNeedOnboarding?: () => void;
  onSignedOut?: () => void;
};

export type PortalSessionGateState = {
  checking: boolean;
  denied: boolean;
  errorDetail: string;
  session: SessionContext | null;
};

/**
 * Shared portal entry check: optional onboarding → session-context → canAccessPortal.
 * Portals keep their own loading/denied chrome; this owns the fetch logic.
 */
export function usePortalSessionGate(options: UsePortalSessionGateOptions): PortalSessionGateState {
  const {
    portal,
    apiUrl,
    isLoaded,
    isSignedIn,
    getToken,
    skipCheck = false,
    fetchOnboarding,
    onSession,
    onNeedOnboarding,
    onSignedOut,
  } = options;

  const [checking, setChecking] = useState(!skipCheck);
  const [denied, setDenied] = useState(false);
  const [errorDetail, setErrorDetail] = useState("");
  const [session, setSession] = useState<SessionContext | null>(null);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      setSession(null);
      setDenied(false);
      setErrorDetail("");
      setChecking(false);
      onSignedOut?.();
      return;
    }
    if (skipCheck) {
      setChecking(false);
      return;
    }

    let cancelled = false;
    void (async () => {
      setChecking(true);
      setDenied(false);
      setErrorDetail("");
      try {
        const token = await getToken();
        if (!token) throw new Error("missing_token");

        if (fetchOnboarding) {
          const onboarding = await fetchOnboarding(token);
          if (cancelled) return;
          if (!onboarding.ready) {
            // Keep checking=true so children do not flash before navigation.
            onNeedOnboarding?.();
            return;
          }
        }

        const ctx = await fetchSessionContext(apiUrl, token);
        if (cancelled) return;
        if (!canAccessPortal(ctx.permissions, portal)) {
          setDenied(true);
          setErrorDetail("missing_portal_permission");
          setChecking(false);
          return;
        }
        setSession(ctx);
        onSession?.(ctx);
        setChecking(false);
      } catch (err) {
        if (cancelled) return;
        // Do NOT treat session-context failures as onboarding — that loops dashboard ↔ onboarding.
        setErrorDetail(err instanceof Error ? err.message : "session_failed");
        setChecking(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    apiUrl,
    fetchOnboarding,
    getToken,
    isLoaded,
    isSignedIn,
    onNeedOnboarding,
    onSession,
    onSignedOut,
    portal,
    skipCheck,
  ]);

  return { checking, denied, errorDetail, session };
}
