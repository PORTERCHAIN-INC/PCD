"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
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
      <div className="flex min-h-dvh items-center justify-center bg-[var(--gray-bg)]">
        <p className="text-sm text-[var(--muted)]">Loading activation status…</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-[var(--gray-bg)] p-6">
        <div className="max-w-md rounded-2xl bg-white p-6 text-center shadow-sm">
          <p className="text-sm text-red-600">{error}</p>
          <button
            type="button"
            onClick={() => void refresh()}
            className="mt-4 rounded-xl bg-[var(--secondary)] px-4 py-2 text-sm font-semibold text-white"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <DriverOnboardingView
      data={data}
      onRefresh={() => void refresh()}
      refreshing={loading}
    />
  );
}
