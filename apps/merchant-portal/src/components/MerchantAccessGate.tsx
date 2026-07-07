"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { fetchMerchantAccess } from "@/lib/merchant-access";
import { fetchMerchantOnboarding, isPendingMerchantPath } from "@/lib/onboarding";
import { isClerkConfigured } from "@/lib/env";

type Props = {
  children: ReactNode;
  onProfile?: (profile: import("@/lib/merchant-access").MerchantAccessProfile) => void;
};

export default function MerchantAccessGate({ children, onProfile }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const { isLoaded, isSignedIn } = useAuth();
  const { getApiToken } = useMerchantAuth();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (!isClerkConfigured()) {
      setChecking(false);
      return;
    }
    if (!isLoaded) return;
    if (!isSignedIn) {
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
      try {
        const token = await getApiToken();
        const onboarding = await fetchMerchantOnboarding(token);
        if (!onboarding.ready) {
          router.replace("/onboarding");
          return;
        }
        const profile = await fetchMerchantAccess(token);
        if (!cancelled) {
          onProfile?.(profile);
          setChecking(false);
        }
      } catch {
        if (!cancelled) router.replace("/onboarding");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [getApiToken, isLoaded, isSignedIn, onProfile, pathname, router]);

  if (!isClerkConfigured()) {
    return <>{children}</>;
  }

  if (!isLoaded || checking) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-secondary border-t-transparent" />
        <p className="text-sm text-muted">Verifying merchant access…</p>
      </div>
    );
  }

  return <>{children}</>;
}
