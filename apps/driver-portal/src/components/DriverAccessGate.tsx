"use client";

import { useCallback, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { SignOutButton, useAuth } from "@clerk/nextjs";
import { LogOut } from "lucide-react";
import {
  humanAuthError,
  platformLoginUrl,
  useOptionalSessionContext,
  usePortalSessionGate,
  type SessionContext,
} from "@porterchain/auth";
import { isClerkConfigured, isDevEmailLogin, publicEnv } from "@/lib/env";
import { fetchDriverOnboarding, isPendingDriverPath } from "@/lib/onboarding";

type Props = {
  children: ReactNode;
};

export default function DriverAccessGate({ children }: Props) {
  if (!isClerkConfigured()) {
    return <>{children}</>;
  }
  // Local email picker: middleware + BFF cookie; do not wait on Clerk isLoaded.
  if (isDevEmailLogin()) {
    return <>{children}</>;
  }
  return <DriverAccessGateWithClerk>{children}</DriverAccessGateWithClerk>;
}

function DriverAccessGateWithClerk({ children }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const sessionCtx = useOptionalSessionContext();
  const setSession = sessionCtx?.setSession;
  const setActiveWorkspaceId = sessionCtx?.setActiveWorkspaceId;
  const onPendingPath = isPendingDriverPath(pathname);

  const onSession = useCallback(
    (ctx: SessionContext) => {
      setSession?.(ctx);
      if (ctx.default_workspace) {
        setActiveWorkspaceId?.(ctx.default_workspace);
      }
    },
    [setActiveWorkspaceId, setSession]
  );

  const onSignedOut = useCallback(() => {
    setSession?.(null);
    router.replace("/login");
  }, [router, setSession]);

  const onNeedOnboarding = useCallback(() => {
    router.replace("/onboarding");
  }, [router]);

  const fetchOnboarding = useCallback(async () => fetchDriverOnboarding(), []);

  const { errorDetail } = usePortalSessionGate({
    portal: "driver",
    apiUrl: publicEnv.porterchainApiUrl,
    isLoaded,
    isSignedIn: !!isSignedIn,
    getToken,
    skipCheck: onPendingPath,
    // Driver BFF onboarding uses cookies; token is unused but required by the shared hook.
    fetchOnboarding,
    onSession,
    onSignedOut,
    onNeedOnboarding,
  });

  // Local email-picker session: middleware + BFF enforce cookie; skip Clerk gate.
  if (isLoaded && !isSignedIn && isDevEmailLogin()) {
    return <>{children}</>;
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
            {humanAuthError(
              errorDetail,
              errorDetail === "missing_portal_permission"
                ? "This account is not provisioned for the Driver portal."
                : `Could not load your session (${errorDetail}).`
            )}
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
