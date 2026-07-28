"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { fetchCustomerAccess } from "@/lib/customer-access";
import { fetchCustomerOnboarding, isPendingCustomerPath } from "@/lib/onboarding";
import { isClerkConfigured } from "@/lib/env";

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
  const onPendingPath = isPendingCustomerPath(pathname);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      router.replace("/sign-in");
      return;
    }
    if (onPendingPath) return;

    let cancelled = false;
    void (async () => {
      setChecking(true);
      try {
        const token = await getToken();
        if (!token) throw new Error("missing_token");
        const onboarding = await fetchCustomerOnboarding(token);
        if (!onboarding.ready) {
          router.replace("/onboarding");
          return;
        }
        await fetchCustomerAccess(token);
        if (!cancelled) setChecking(false);
      } catch {
        if (!cancelled) router.replace("/onboarding");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [getToken, isLoaded, isSignedIn, onPendingPath, pathname, router]);

  if (!isLoaded || (checking && !onPendingPath)) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-secondary border-t-transparent" />
        <p className="text-sm text-muted">Verifying customer access…</p>
      </div>
    );
  }

  return <>{children}</>;
}
