"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { fetchCustomerOnboarding, isPendingCustomerPath } from "@/lib/onboarding";
import { isClerkConfigured, publicEnv } from "@/lib/env";
import {
  canAccessPortal,
  fetchSessionContext,
  platformLoginUrl,
  useOptionalSessionContext,
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
  const sessionBag = useOptionalSessionContext();
  const setSession = sessionBag?.setSession;
  const setActiveWorkspaceId = sessionBag?.setActiveWorkspaceId;
  const onPendingPath = isPendingCustomerPath(pathname);
  const [checking, setChecking] = useState(true);
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      setSession?.(null);
      router.replace("/sign-in");
      return;
    }
    if (onPendingPath) return;

    let cancelled = false;
    void (async () => {
      setChecking(true);
      setDenied(false);
      try {
        const token = await getToken();
        if (!token) throw new Error("missing_token");
        const onboarding = await fetchCustomerOnboarding(token);
        if (!onboarding.ready) {
          router.replace("/onboarding");
          return;
        }
        const ctx = await fetchSessionContext(publicEnv.porterchainApiUrl, token);
        if (cancelled) return;
        if (!canAccessPortal(ctx.permissions, "customer")) {
          setDenied(true);
          setChecking(false);
          return;
        }
        setSession?.(ctx);
        if (ctx.default_workspace) {
          setActiveWorkspaceId?.(ctx.default_workspace);
        }
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
    getToken,
    isLoaded,
    isSignedIn,
    onPendingPath,
    pathname,
    router,
    setSession,
    setActiveWorkspaceId,
  ]);

  if (!isLoaded || (checking && !onPendingPath)) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-secondary border-t-transparent" />
        <p className="text-sm text-muted">Loading session…</p>
      </div>
    );
  }

  if (denied) {
    const loginUrl = platformLoginUrl(publicEnv.websiteUrl);
    return (
      <div className="mx-auto flex min-h-[50vh] max-w-md flex-col items-center justify-center gap-3 p-6 text-center">
        <h1 className="text-lg font-semibold text-primary">Access denied</h1>
        <p className="text-sm text-muted">
          This account is not provisioned for the Customer portal.
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
