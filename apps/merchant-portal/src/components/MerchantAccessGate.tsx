"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { Spinner } from "@porterchain/ui/loading";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { merchantProfileFromSession } from "@/lib/merchant-access";
import { fetchMerchantOnboarding, isPendingMerchantPath } from "@/lib/onboarding";
import { isClerkConfigured, publicEnv } from "@/lib/env";
import {
  canAccessPortal,
  fetchSessionContext,
  platformLoginUrl,
  useOptionalSessionContext,
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
  const [checking, setChecking] = useState(true);
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      setSession?.(null);
      router.replace("/sign-in");
      return;
    }
    if (isPendingMerchantPath(pathname)) {
      setChecking(false);
      return;
    }

    let cancelled = false;
    void (async () => {
      setChecking(true);
      setDenied(false);
      try {
        const token = await getApiToken();
        const onboarding = await fetchMerchantOnboarding(token);
        if (!onboarding.ready) {
          router.replace("/onboarding");
          return;
        }
        const ctx = await fetchSessionContext(publicEnv.porterchainApiUrl, token);
        if (cancelled) return;
        if (!canAccessPortal(ctx.permissions, "merchant")) {
          setDenied(true);
          setChecking(false);
          return;
        }
        setSession?.(ctx);
        if (ctx.default_workspace) {
          setActiveWorkspaceId?.(ctx.default_workspace);
        }
        onProfile?.(merchantProfileFromSession(ctx));
        setChecking(false);
      } catch {
        if (!cancelled) {
          router.replace("/onboarding");
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    getApiToken,
    isLoaded,
    isSignedIn,
    onProfile,
    pathname,
    router,
    setSession,
    setActiveWorkspaceId,
  ]);

  if (!isLoaded || checking) {
    return <Spinner label="Loading session…" />;
  }

  if (denied) {
    const loginUrl = platformLoginUrl(publicEnv.websiteUrl);
    return (
      <div className="mx-auto flex min-h-[50vh] max-w-md flex-col items-center justify-center gap-3 p-6 text-center">
        <h1 className="text-lg font-semibold text-primary">Access denied</h1>
        <p className="text-sm text-muted">
          This account is not provisioned for the Merchant portal.
        </p>
        <a
          href={loginUrl}
          className="mt-2 inline-flex rounded-xl bg-secondary px-4 py-2.5 text-sm font-semibold text-white"
        >
          Back to Platform login
        </a>
      </div>
    );
  }

  return <>{children}</>;
}
