"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { KeyRound, LogOut } from "lucide-react";
import { Spinner } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import type { AdminStaffProfile } from "@/lib/admin-access";
import { publicEnv } from "@/lib/env";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";
import { clearStaffSession } from "@/lib/staff-session";
import { fetchStaffSecurityStatus } from "@/lib/staff-security";
import {
  humanAuthError,
  useOptionalSessionContext,
  usePortalSessionGate,
  type SessionContext,
} from "@porterchain/auth";

type Props = {
  children: ReactNode;
};

function profileFromSession(ctx: SessionContext): AdminStaffProfile {
  return {
    user_id: ctx.legacy_profile_ids?.admin_user_id ?? ctx.user_id,
    email: ctx.email ?? "",
    name: null,
    role: ctx.roles[0] ?? "admin",
    is_active: ctx.status === "active",
  };
}

function PasskeyRecommendBanner({ show }: { show: boolean }) {
  const pathname = usePathname();
  if (!show || pathname?.startsWith("/account/security")) return null;
  return (
    <div className="border-b border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-950">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2">
        <p className="inline-flex items-center gap-2">
          <KeyRound className="h-4 w-4 shrink-0" />
          Add a passkey for phishing-resistant sign-in and step-up on sensitive actions.
        </p>
        <Link
          href="/account/security"
          className="font-semibold text-amber-900 underline underline-offset-2"
        >
          Account → Security
        </Link>
      </div>
    </div>
  );
}

export default function AdminAccessGate({ children }: Props) {
  const router = useRouter();
  const { isLoaded, isSignedIn, getApiToken, authReady } = useAdminAuth();
  const { setProfile } = useAdminProfile();
  const sessionCtx = useOptionalSessionContext();
  const setSession = sessionCtx?.setSession;
  const setActiveWorkspaceId = sessionCtx?.setActiveWorkspaceId;
  const [passkeyRecommended, setPasskeyRecommended] = useState(false);

  const onSession = useCallback(
    (ctx: SessionContext) => {
      setSession?.(ctx);
      if (ctx.default_workspace) {
        setActiveWorkspaceId?.(ctx.default_workspace);
      }
      setProfile(profileFromSession(ctx));
    },
    [setActiveWorkspaceId, setProfile, setSession]
  );

  const onSignedOut = useCallback(() => {
    setProfile(null);
    setSession?.(null);
    router.replace("/sign-in");
  }, [router, setProfile, setSession]);

  const handleSignOut = useCallback(() => {
    void clearStaffSession(publicEnv.porterchainApiUrl).then(() => {
      setProfile(null);
      setSession?.(null);
      router.replace("/sign-in");
    });
  }, [router, setProfile, setSession]);

  const { checking, errorDetail } = usePortalSessionGate({
    portal: "admin",
    apiUrl: "/api/porterchain",
    isLoaded,
    isSignedIn: !!isSignedIn,
    getToken: getApiToken,
    onSession,
    onSignedOut,
  });

  useEffect(() => {
    if (!authReady) return;
    let cancelled = false;
    void (async () => {
      try {
        const token = await getApiToken();
        const status = await fetchStaffSecurityStatus(token);
        if (!cancelled) setPasskeyRecommended(Boolean(status.passkey_recommended));
      } catch {
        /* soft fail */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authReady, getApiToken]);

  if (!isLoaded || checking) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-3 bg-gray-bg">
        <Spinner />
        <p className="text-sm text-muted">Loading session…</p>
      </div>
    );
  }

  if (errorDetail) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-gray-bg p-6">
        <div className="max-w-md rounded-2xl border border-primary/10 bg-white p-8 text-center shadow-sm">
          <h1 className="text-xl font-bold text-primary">
            {errorDetail === "missing_portal_permission" ? "Access denied" : "Session error"}
          </h1>
          <p className="mt-2 text-sm text-muted">
            {humanAuthError(
              errorDetail,
              errorDetail === "missing_portal_permission"
                ? "This account is not provisioned for the Admin portal."
                : `Could not load your session (${errorDetail}).`
            )}
          </p>
          <Link
            href="/sign-in"
            className="mt-6 flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-2.5 text-sm font-semibold text-white hover:bg-secondary/90"
          >
            Back to staff sign-in
          </Link>
          <button
            type="button"
            onClick={handleSignOut}
            className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-red-200 bg-white px-4 py-2.5 text-sm font-semibold text-red-600 hover:bg-red-50"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <PasskeyRecommendBanner show={passkeyRecommended} />
      {children}
    </>
  );
}
