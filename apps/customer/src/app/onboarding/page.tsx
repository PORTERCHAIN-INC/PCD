"use client";

import dynamic from "next/dynamic";

const OnboardingPageClient = dynamic(() => import("@/components/onboarding/OnboardingPageClient"), {
  loading: () => <p className="p-8 text-sm text-muted">Loading…</p>,
});

export default function OnboardingPage() {
  return <OnboardingPageClient />;
}
