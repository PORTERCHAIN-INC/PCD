"use client";

import dynamic from "next/dynamic";
import { PageSkeleton } from "@porterchain/ui/loading";

const OnboardingPageClient = dynamic(() => import("@/components/onboarding/OnboardingPageClient"), {
  loading: () => <PageSkeleton rows={3} />,
});

export default function OnboardingPage() {
  return <OnboardingPageClient />;
}
