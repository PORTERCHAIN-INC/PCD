"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { SignOutButton, useAuth } from "@clerk/nextjs";
import { LogOut } from "lucide-react";
import { Spinner } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import type { AdminStaffProfile } from "@/lib/admin-access";
import { isClerkConfigured, publicEnv } from "@/lib/env";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";
import {
  canAccessPortal,
  fetchSessionContext,
  platformLoginUrl,
  useOptionalSessionContext,
} from "@porterchain/auth";

type Props = {
  children: ReactNode;
};

function profileFromSession(
  ctx: Awaited<ReturnType<typeof fetchSessionContext>>
): AdminStaffProfile {
  return {
    user_id: ctx.legacy_profile_ids?.admin_user_id ?? ctx.user_id,
    email: ctx.email ?? "",
    name: null,
    role: ctx.roles[0] ?? "admin",
    is_active: ctx.status === "active",
  };
}

export default function AdminAccessGate({ children }: Props) {
  if (!isClerkConfigured()) {
    return <>{children}</>;
  }
  return <AdminAccessGateWithClerk>{children}</AdminAccessGateWithClerk>;
}

function AdminAccessGateWithClerk({ children }: Props) {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();
  const { getApiToken } = useAdminAuth();
  const { profile, setProfile } = useAdminProfile();
  const sessionCtx = useOptionalSessionContext();
  const setSession = sessionCtx?.setSession;
  const setActiveWorkspaceId = sessionCtx?.setActiveWorkspaceId;
  const [checking, setChecking] = useState(!profile);
  const [errorDetail, setErrorDetail] = useState("");

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      setProfile(null);
      setSession?.(null);
      router.replace("/sign-in");
      return;
    }

    let cancelled = false;
    void (async () => {
      setChecking(true);
      setErrorDetail("");
      try {
        const token = await getApiToken();
        const ctx = await fetchSessionContext(publicEnv.porterchainApiUrl, token);
        if (cancelled) return;
        if (!canAccessPortal(ctx.permissions, "admin")) {
          throw new Error("missing_portal_permission");
        }
        setSession?.(ctx);
        if (ctx.default_workspace) {
          setActiveWorkspaceId?.(ctx.default_workspace);
        }
        setProfile(profileFromSession(ctx));
        setChecking(false);
      } catch (err) {
        if (cancelled) return;
        setProfile(null);
        setSession?.(null);
        setErrorDetail(err instanceof Error ? err.message : "session_failed");
        setChecking(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isLoaded, isSignedIn, getApiToken, router, setProfile, setSession, setActiveWorkspaceId]);

  if (!isLoaded || checking) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-3 bg-gray-bg">
        <Spinner />
        <p className="text-sm text-muted">Loading session…</p>
      </div>
    );
  }

  if (errorDetail) {
    const loginUrl = platformLoginUrl(publicEnv.websiteUrl);
    const denied = errorDetail === "missing_portal_permission";
    return (
      <div className="flex min-h-dvh items-center justify-center bg-gray-bg p-6">
        <div className="max-w-md rounded-2xl border border-primary/10 bg-white p-8 text-center shadow-sm">
          <h1 className="text-xl font-bold text-primary">
            {denied ? "Access denied" : "Session error"}
          </h1>
          <p className="mt-2 text-sm text-muted">
            {denied
              ? "This account is not provisioned for the Admin portal."
              : errorDetail === "porterchain_api_timeout"
                ? "Porterchain API did not respond. Start the API on port 8001 and refresh."
                : `Could not load your session (${errorDetail}).`}
          </p>
          <a
            href={loginUrl}
            className="mt-6 flex w-full items-center justify-center rounded-xl bg-secondary px-4 py-2.5 text-sm font-semibold text-white hover:bg-secondary/90"
          >
            Back to Platform login
          </a>
          <SignOutButton redirectUrl={loginUrl}>
            <button
              type="button"
              className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-red-200 bg-white px-4 py-2.5 text-sm font-semibold text-red-600 hover:bg-red-50"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </SignOutButton>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
