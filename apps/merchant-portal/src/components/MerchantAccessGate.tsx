"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { Spinner } from "@porterchain/ui/loading";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { fetchMerchantAccess } from "@/lib/merchant-access";
import { fetchMerchantOnboarding, isPendingMerchantPath } from "@/lib/onboarding";
import { isClerkConfigured } from "@/lib/env";

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
  const [checking, setChecking] = useState(true);

  useEffect(() => {
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

  if (!isLoaded || checking) {
    return <Spinner label="Verifying merchant access…" />;
  }

  return <>{children}</>;
}
