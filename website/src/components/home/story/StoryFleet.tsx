"use client";

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import LinkButton from "@/components/corporate/ui/LinkButton";
import StorySection from "@/components/home/story/StorySection";

const FleetSelector = dynamic(() => import("@/components/shared/FleetSelector"), {
  loading: () => (
    <div
      className="min-h-[320px] sm:min-h-[380px] rounded-3xl border border-primary/8 bg-white animate-pulse"
      aria-hidden
    />
  ),
  ssr: false,
});

export default function StoryFleet() {
  const t = useTranslations("corporate.home.story.fleet");

  return (
    <StorySection
      id="fleet"
      label={t("label")}
      title={t("title")}
      subtitle={t("subtitle")}
      className="bg-gray-bg"
      tight
    >
      <FleetSelector detailed={false} />
      <div className="mt-8">
        <LinkButton href="/business#fleet" variant="outline" showArrow trackSource="home-fleet">
          {t("cta")}
        </LinkButton>
      </div>
    </StorySection>
  );
}
