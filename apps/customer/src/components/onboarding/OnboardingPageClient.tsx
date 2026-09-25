"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import PortalOnboardingView from "@/components/onboarding/PortalOnboardingView";
import { useCustomerOnboarding } from "@/hooks/useCustomerOnboarding";
import { isClerkConfigured } from "@/lib/env";

export default function OnboardingPageClient() {
  if (!isClerkConfigured()) {
    return <RedirectToDashboard />;
  }
  return <CustomerOnboardingWithClerk />;
}

function RedirectToDashboard() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/dashboard");
  }, [router]);
  return null;
}

function CustomerOnboardingWithClerk() {
  const router = useRouter();
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const { data, loading, error, refresh, setLoading } = useCustomerOnboarding(30_000);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      router.replace("/sign-in?redirect_url=/onboarding");
      return;
    }
    let cancelled = false;
    let timer: number | undefined;
    void (async () => {
      const token = await getToken();
      if (!token || cancelled) return;
      const status = await refresh(token);
      if (status?.ready) {
        router.replace("/dashboard");
        return;
      }
      timer = window.setInterval(async () => {
        const t = await getToken();
        if (!t) return;
        const next = await refresh(t);
        if (next?.ready) router.replace("/dashboard");
      }, 30_000);
    })();
    return () => {
      cancelled = true;
      if (timer) window.clearInterval(timer);
    };
  }, [getToken, isLoaded, isSignedIn, refresh, router]);

  if ((loading && !data) || !isLoaded) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-gray-bg">
        <p className="text-sm text-muted">Loading activation status…</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-gray-bg p-6">
        <div className="max-w-md rounded-2xl bg-white p-6 text-center shadow-sm">
          <p className="text-sm text-red-600">{error}</p>
          <button
            type="button"
            onClick={() => {
              setLoading(true);
              void getToken().then((t) => {
                if (t) void refresh(t);
              });
            }}
            className="mt-4 rounded-xl bg-secondary px-4 py-2 text-sm font-semibold text-white"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <PortalOnboardingView
      portalTitle="Porterchain Customer"
      portalSubtitle="Account activation"
      data={data}
      refreshing={loading}
      onRefresh={() => {
        void getToken().then((t) => {
          if (t) void refresh(t);
        });
      }}
      footerNote="Add a verified email in Clerk if the email step is pending. Contact support if identity conflict appears."
    />
  );
}
