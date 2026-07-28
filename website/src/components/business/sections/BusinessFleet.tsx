"use client";

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import StorySection from "@/components/home/story/StorySection";
import ShimmerButton from "@/components/magic/shimmer-button";

const FleetSelector = dynamic(() => import("@/components/shared/FleetSelector"), {
  loading: () => (
    <div className="space-y-4" aria-hidden>
      <div className="flex gap-2 overflow-hidden">
        {Array.from({ length: 7 }).map((_, i) => (
          <div
            key={i}
            className="h-14 w-36 shrink-0 rounded-2xl border border-secondary/15 bg-secondary/10 animate-pulse"
          />
        ))}
      </div>
      <div className="grid lg:grid-cols-[1.35fr_0.9fr] overflow-hidden rounded-3xl border border-secondary/15 bg-white">
        <div className="h-64 sm:h-80 lg:h-[22rem] bg-gradient-to-br from-secondary/10 to-gray-bg animate-pulse" />
        <div className="space-y-3 p-6">
          <div className="h-4 w-20 rounded bg-secondary/15 animate-pulse" />
          <div className="h-8 w-2/3 rounded bg-primary/10 animate-pulse" />
          <div className="h-16 w-full rounded bg-primary/5 animate-pulse" />
          <div className="grid grid-cols-2 gap-2.5 pt-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-16 rounded-2xl bg-secondary/10 animate-pulse" />
            ))}
          </div>
        </div>
      </div>
    </div>
  ),
  ssr: false,
});

export default function BusinessFleet() {
  const t = useTranslations("businessPage.fleet");

  return (
    <StorySection
      id="fleet"
      label={t("label")}
      title={t("title")}
      subtitle={t("subtitle")}
      className="bg-gray-bg grid-pattern scroll-mt-24"
    >
      <FleetSelector detailed showPreview />
      <div className="mt-8 flex justify-center">
        <ShimmerButton
          href="/contact?intent=quote&from=business-fleet"
          trackSource="business-fleet"
        >
          {t("quoteCta")}
        </ShimmerButton>
      </div>
    </StorySection>
  );
}
