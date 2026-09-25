"use client";

import { useEffect, useRef, useState } from "react";
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
  /**
   * When set, called after onboarding. Non-null skips `/session-context`
   * (e.g. merchant ACTIVE session already proves portal access).
   */
  resolveSession?: (token: string) => Promise<SessionContext | null>;
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
 * Completes once per signed-in session — callback identity churn does not re-fetch.
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
    resolveSession,
    onSession,
    onNeedOnboarding,
    onSignedOut,
  } = options;

  const [checking, setChecking] = useState(!skipCheck);
  const [denied, setDenied] = useState(false);
  const [errorDetail, setErrorDetail] = useState("");
  const [session, setSession] = useState<SessionContext | null>(null);
  const gatedRef = useRef(false);

  const getTokenRef = useRef(getToken);
  getTokenRef.current = getToken;
  const fetchOnboardingRef = useRef(fetchOnboarding);
  fetchOnboardingRef.current = fetchOnboarding;
  const resolveSessionRef = useRef(resolveSession);
  resolveSessionRef.current = resolveSession;
  const onSessionRef = useRef(onSession);
  onSessionRef.current = onSession;
  const onNeedOnboardingRef = useRef(onNeedOnboarding);
  onNeedOnboardingRef.current = onNeedOnboarding;
  const onSignedOutRef = useRef(onSignedOut);
  onSignedOutRef.current = onSignedOut;

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      gatedRef.current = false;
      setSession(null);
      setDenied(false);
      setErrorDetail("");
      setChecking(false);
      onSignedOutRef.current?.();
      return;
    }
    if (skipCheck) {
      setChecking(false);
      return;
    }
    // Already passed gate for this signed-in session — do not re-hit APIs.
    if (gatedRef.current) {
      setChecking(false);
      return;
    }

    let cancelled = false;
    void (async () => {
      setChecking(true);
      setDenied(false);
      setErrorDetail("");
      try {
        const token = await getTokenRef.current();
        if (!token) throw new Error("missing_token");

        const onboard = fetchOnboardingRef.current;
        if (onboard) {
          const onboarding = await onboard(token);
          if (cancelled) return;
          if (!onboarding.ready) {
            onNeedOnboardingRef.current?.();
            return;
          }
        }

        const resolved = await resolveSessionRef.current?.(token);
        if (cancelled) return;
        const ctx = resolved ?? (await fetchSessionContext(apiUrl, token, portal));
        if (cancelled) return;
        if (!canAccessPortal(ctx.permissions, portal)) {
          setDenied(true);
          setErrorDetail("missing_portal_permission");
          setChecking(false);
          return;
        }
        gatedRef.current = true;
        setSession(ctx);
        onSessionRef.current?.(ctx);
        setChecking(false);
      } catch (err) {
        if (cancelled) return;
        setErrorDetail(err instanceof Error ? err.message : "session_failed");
        setChecking(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [apiUrl, isLoaded, isSignedIn, portal, skipCheck]);

  return { checking, denied, errorDetail, session };
}
