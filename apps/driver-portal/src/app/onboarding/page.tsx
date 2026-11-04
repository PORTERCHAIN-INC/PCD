"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { PageSkeleton } from "@porterchain/ui/loading";
import DriverOnboardingView from "@/components/onboarding/DriverOnboardingView";
import { useDriverOnboarding } from "@/hooks/useDriverOnboarding";
import { hasDriverSession } from "@/lib/api";

export default function OnboardingPage() {
  const router = useRouter();
  const { data, loading, error, refresh } = useDriverOnboarding(30_000);

  useEffect(() => {
    void hasDriverSession().then((ok) => {
      if (!ok) router.replace("/login?redirect_url=/onboarding");
    });
  }, [router]);

  useEffect(() => {
    if (data?.ready) {
      router.replace("/dashboard");
    }
  }, [data?.ready, router]);

  if (loading && !data) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-[var(--gray-bg)] p-6">
        <PageSkeleton rows={3} />
      </div>
    );
  }

  if (error && !data) {
    // L167: drivers are invite-only. Never show raw API codes.
    const notInvited = /not_provisioned|forbidden|403/i.test(error);
    const title = notInvited
      ? "Driver accounts are by invitation."
      : "We could not load your driver account.";
    const body = notInvited
      ? "Contact PorterChain ops to get an invite."
      : "Please try again. If it keeps happening, contact PorterChain ops.";
    return (
      <div className="flex min-h-dvh items-center justify-center bg-[var(--gray-bg)] p-6">
        <div className="max-w-md rounded-2xl bg-white p-6 text-center shadow-sm">
          <h1 className="text-lg font-semibold text-gray-900">{title}</h1>
          <p className="mt-2 text-sm text-gray-600">{body}</p>
          {!notInvited && (
            <button
              type="button"
              onClick={() => void refresh()}
              className="mt-4 rounded-xl bg-[var(--secondary)] px-4 py-2 text-sm font-semibold text-white"
            >
              Retry
            </button>
          )}
          <a
            href="/auth/logout"
            className="mt-4 ml-2 inline-block rounded-xl border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700"
          >
            {notInvited ? "Sign out and go back" : "Sign out"}
          </a>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return <DriverOnboardingView data={data} onRefresh={() => void refresh()} refreshing={loading} />;
}
