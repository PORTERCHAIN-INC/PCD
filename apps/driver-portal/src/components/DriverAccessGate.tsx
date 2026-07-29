"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { SignOutButton, useAuth } from "@clerk/nextjs";
import { LogOut } from "lucide-react";
import {
  canAccessPortal,
  fetchSessionContext,
  platformLoginUrl,
  useOptionalSessionContext,
} from "@porterchain/auth";
import { isClerkConfigured, publicEnv } from "@/lib/env";

type Props = {
  children: ReactNode;
};

export default function DriverAccessGate({ children }: Props) {
  if (!isClerkConfigured()) {
    return <>{children}</>;
  }
  return <DriverAccessGateWithClerk>{children}</DriverAccessGateWithClerk>;
}

function DriverAccessGateWithClerk({ children }: Props) {
  const router = useRouter();
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const sessionCtx = useOptionalSessionContext();
  const setSession = sessionCtx?.setSession;
  const setActiveWorkspaceId = sessionCtx?.setActiveWorkspaceId;
  const [checking, setChecking] = useState(true);
  const [errorDetail, setErrorDetail] = useState("");

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      setSession?.(null);
      router.replace("/login");
      return;
    }

    let cancelled = false;
    void (async () => {
      setChecking(true);
      setErrorDetail("");
      try {
        const token = await getToken();
        if (!token) throw new Error("missing_token");
        const ctx = await fetchSessionContext(publicEnv.porterchainApiUrl, token);
        if (cancelled) return;
        if (!canAccessPortal(ctx.permissions, "driver")) {
          throw new Error("missing_portal_permission");
        }
        setSession?.(ctx);
        if (ctx.default_workspace) {
          setActiveWorkspaceId?.(ctx.default_workspace);
        }
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
  }, [isLoaded, isSignedIn, getToken, router, setSession, setActiveWorkspaceId]);

  if (!isLoaded || checking) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-3 bg-gray-bg">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-secondary border-t-transparent" />
        <p className="text-sm text-muted">Loading session…</p>
      </div>
    );
  }

  if (errorDetail) {
    const loginUrl = platformLoginUrl(publicEnv.websiteUrl);
    return (
      <div className="flex min-h-dvh items-center justify-center bg-gray-bg p-6">
        <div className="max-w-md rounded-2xl border border-primary/10 bg-white p-8 text-center shadow-sm">
          <h1 className="text-xl font-bold text-primary">
            {errorDetail === "missing_portal_permission" ? "Access denied" : "Session error"}
          </h1>
          <p className="mt-2 text-sm text-muted">
            {errorDetail === "missing_portal_permission"
              ? "This account is not provisioned for the Driver portal."
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
