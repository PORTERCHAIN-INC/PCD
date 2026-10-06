"use client";

import dynamic from "next/dynamic";
import { PageSkeleton } from "@porterchain/ui/loading";

const OnboardingPageClient = dynamic(() => import("@/components/onboarding/OnboardingPageClient"), {
  loading: () => (
    <div className="p-8">
      <PageSkeleton rows={4} />
    </div>
  ),
});

export default function OnboardingPage() {
  return <OnboardingPageClient />;
}
