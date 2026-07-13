"use client";

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import StorySection from "@/components/home/story/StorySection";
import ShimmerButton from "@/components/magic/shimmer-button";

const FleetSelector = dynamic(() => import("@/components/shared/FleetSelector"), {
  loading: () => (
    <div className="flex gap-2 overflow-hidden sm:grid sm:grid-cols-4 md:grid-cols-7" aria-hidden>
      {Array.from({ length: 7 }).map((_, i) => (
        <div
          key={i}
          className="h-36 min-w-[8.5rem] shrink-0 rounded-2xl sm:rounded-3xl border border-secondary/20 bg-secondary/30 animate-pulse sm:min-w-0"
        />
      ))}
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
      <FleetSelector detailed showPreview={false} />
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
