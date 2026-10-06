"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { PageSkeleton } from "@porterchain/ui/loading";
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
  const { isLoaded, isSignedIn } = useAuth();
  const { data, loading, error, refresh } = useCustomerOnboarding(30_000);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      router.replace("/sign-in?redirect_url=/onboarding");
      return;
    }
    if (data?.ready) router.replace("/dashboard");
  }, [data?.ready, isLoaded, isSignedIn, router]);

  if ((loading && !data) || !isLoaded) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-gray-bg p-6">
        <PageSkeleton rows={3} />
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
            onClick={() => void refresh()}
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
      onRefresh={() => void refresh()}
      footerNote="Add a verified email in Clerk if the email step is pending. Contact support if identity conflict appears."
    />
  );
}
