"use client";

import { useCallback, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { SignOutButton, useAuth } from "@clerk/nextjs";
import { LogOut } from "lucide-react";
import { fetchCustomerOnboarding, isPendingCustomerPath } from "@/lib/onboarding";
import { isClerkConfigured, publicEnv } from "@/lib/env";
import {
  platformLoginUrl,
  useOptionalSessionContext,
  usePortalSessionGate,
  type SessionContext,
} from "@porterchain/auth";

type Props = {
  children: ReactNode;
};

export default function CustomerAccessGate({ children }: Props) {
  if (!isClerkConfigured()) {
    return <>{children}</>;
  }
  return <CustomerAccessGateWithClerk>{children}</CustomerAccessGateWithClerk>;
}

function CustomerAccessGateWithClerk({ children }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const sessionCtx = useOptionalSessionContext();
  const setSession = sessionCtx?.setSession;
  const setActiveWorkspaceId = sessionCtx?.setActiveWorkspaceId;
  const onPendingPath = isPendingCustomerPath(pathname);

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
    router.replace("/sign-in");
  }, [router, setSession]);

  const onNeedOnboarding = useCallback(() => {
    router.replace("/onboarding");
  }, [router]);

  const { checking, denied, errorDetail } = usePortalSessionGate({
    portal: "customer",
    apiUrl: publicEnv.porterchainApiUrl,
    isLoaded,
    isSignedIn: !!isSignedIn,
    getToken,
    skipCheck: onPendingPath,
    fetchOnboarding: fetchCustomerOnboarding,
    onSession,
    onSignedOut,
    onNeedOnboarding,
  });

  if (!isLoaded || (checking && !onPendingPath)) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3" role="status">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-secondary border-t-transparent" />
        <p className="text-sm text-muted">Loading session…</p>
      </div>
    );
  }

  if (denied || errorDetail) {
    const loginUrl = platformLoginUrl(publicEnv.websiteUrl);
    const deniedAccess = errorDetail === "missing_portal_permission" || denied;
    return (
      <div className="mx-auto flex min-h-[50vh] max-w-md flex-col items-center justify-center gap-3 p-6 text-center">
        <h1 className="text-lg font-semibold text-primary">
          {deniedAccess ? "Access denied" : "Session error"}
        </h1>
        <p className="text-sm text-muted">
          {deniedAccess
            ? "This account is not provisioned for the Customer portal."
            : errorDetail === "porterchain_api_timeout"
              ? "Porterchain API did not respond. Start the API on port 8001 and refresh."
              : `Could not load your session (${errorDetail || "unknown"}).`}
        </p>
        <a
          href={loginUrl}
          className="mt-2 inline-flex rounded-xl bg-secondary px-4 py-2.5 text-sm font-semibold text-white"
        >
          Back to Platform login
        </a>
        <SignOutButton redirectUrl={loginUrl}>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-red-200 bg-white px-4 py-2.5 text-sm font-semibold text-red-600 hover:bg-red-50"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </SignOutButton>
      </div>
    );
  }

  return <>{children}</>;
}
