"use client";

import { useCallback, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { Spinner } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import type { AdminStaffProfile } from "@/lib/admin-access";
import { publicEnv } from "@/lib/env";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";
import { clearStaffSession } from "@/lib/staff-session";
import {
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

export default function AdminAccessGate({ children }: Props) {
  const router = useRouter();
  const { isLoaded, isSignedIn, getApiToken } = useAdminAuth();
  const { setProfile } = useAdminProfile();
  const sessionCtx = useOptionalSessionContext();
  const setSession = sessionCtx?.setSession;
  const setActiveWorkspaceId = sessionCtx?.setActiveWorkspaceId;

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
    apiUrl: publicEnv.porterchainApiUrl,
    isLoaded,
    isSignedIn: !!isSignedIn,
    getToken: getApiToken,
    onSession,
    onSignedOut,
  });

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
            {errorDetail === "missing_portal_permission"
              ? "This account is not provisioned for the Admin portal."
              : errorDetail === "porterchain_api_timeout"
                ? "Porterchain API did not respond. Start the API on port 8001 and refresh."
                : `Could not load your session (${errorDetail}).`}
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

  return <>{children}</>;
}
