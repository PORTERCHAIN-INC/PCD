"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import PortalOnboardingView from "@/components/onboarding/PortalOnboardingView";
import { fetchMerchantOnboarding } from "@/lib/onboarding";
import { isClerkConfigured } from "@/lib/env";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";

export default function MerchantOnboardingPage() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();
  const { getApiToken } = useMerchantAuth();
  const [data, setData] = useState<import("@/lib/onboarding").PortalOnboardingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = async () => {
    setError("");
    try {
      const token = await getApiToken();
      const status = await fetchMerchantOnboarding(token);
      setData(status);
      return status;
    } catch (err) {
      setError(err instanceof Error ? err.message : "onboarding_fetch_failed");
      return null;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isClerkConfigured()) {
      router.replace("/dashboard");
      return;
    }
    if (!isLoaded) return;
    if (!isSignedIn) {
      router.replace("/sign-in?redirect_url=/onboarding");
      return;
    }

    let cancelled = false;
    let timer: number | undefined;

    void (async () => {
      const status = await refresh();
      if (cancelled) return;
      if (status?.ready) {
        router.replace("/dashboard");
        return;
      }
      timer = window.setInterval(async () => {
        const next = await refresh();
        if (next?.ready) router.replace("/dashboard");
      }, 30_000);
    })();

    return () => {
      cancelled = true;
      if (timer) window.clearInterval(timer);
    };
  }, [getApiToken, isLoaded, isSignedIn, router]);

  if (!isClerkConfigured()) return null;

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
              void refresh();
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
      data={data}
      refreshing={loading}
      onRefresh={() => {
        setLoading(true);
        void refresh();
      }}
    />
  );
}
