"use client";

import { useCallback, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { SignOutButton, useAuth } from "@clerk/nextjs";
import { LogOut } from "lucide-react";
import { Spinner } from "@porterchain/ui/loading";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { merchantProfileFromSession } from "@/lib/merchant-access";
import { fetchMerchantOnboarding, isPendingMerchantPath } from "@/lib/onboarding";
import { isClerkConfigured, publicEnv } from "@/lib/env";
import {
  platformLoginUrl,
  useOptionalSessionContext,
  usePortalSessionGate,
  type SessionContext,
} from "@porterchain/auth";

type Props = {
  children: ReactNode;
  onProfile?: (profile: import("@/lib/merchant-access").MerchantAccessProfile) => void;
};

export default function MerchantAccessGate({ children, onProfile }: Props) {
  if (!isClerkConfigured()) {
    return <>{children}</>;
  }
  return (
    <MerchantAccessGateWithClerk onProfile={onProfile}>{children}</MerchantAccessGateWithClerk>
  );
}

function MerchantAccessGateWithClerk({ children, onProfile }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const { isLoaded, isSignedIn } = useAuth();
  const { getApiToken } = useMerchantAuth();
  const sessionBag = useOptionalSessionContext();
  const setSession = sessionBag?.setSession;
  const setActiveWorkspaceId = sessionBag?.setActiveWorkspaceId;
  const onPendingPath = isPendingMerchantPath(pathname);

  const onSession = useCallback(
    (ctx: SessionContext) => {
      setSession?.(ctx);
      if (ctx.default_workspace) {
        setActiveWorkspaceId?.(ctx.default_workspace);
      }
      onProfile?.(merchantProfileFromSession(ctx));
    },
    [onProfile, setActiveWorkspaceId, setSession]
  );

  const onSignedOut = useCallback(() => {
    setSession?.(null);
    router.replace("/sign-in");
  }, [router, setSession]);

  const onNeedOnboarding = useCallback(() => {
    router.replace("/onboarding");
  }, [router]);

  const { checking, denied, errorDetail } = usePortalSessionGate({
    portal: "merchant",
    apiUrl: publicEnv.porterchainApiUrl,
    isLoaded,
    isSignedIn: !!isSignedIn,
    getToken: getApiToken,
    skipCheck: onPendingPath,
    fetchOnboarding: fetchMerchantOnboarding,
    onSession,
    onSignedOut,
    onNeedOnboarding,
  });

  if (!isLoaded || checking) {
    return <Spinner label="Loading session…" />;
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
            ? "This account is not provisioned for the Merchant portal."
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
