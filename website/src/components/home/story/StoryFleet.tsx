"use client";

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import LinkButton from "@/components/corporate/ui/LinkButton";
import BlurFade from "@/components/magic/blur-fade";
import StorySection from "@/components/home/story/StorySection";

const FleetSelector = dynamic(() => import("@/components/shared/FleetSelector"), {
  loading: () => (
    <div className="flex gap-3 overflow-hidden sm:grid sm:grid-cols-4 md:grid-cols-7" aria-hidden>
      {Array.from({ length: 7 }).map((_, i) => (
        <div
          key={i}
          className="aspect-[4/3] min-w-[9.5rem] shrink-0 rounded-2xl border border-secondary/15 bg-secondary/10 animate-pulse sm:min-w-0"
        />
      ))}
    </div>
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
    >
      <div className="flex flex-col gap-4 sm:gap-5">
        <BlurFade inView>
          <FleetSelector detailed={false} showPreview={false} />
        </BlurFade>
        <BlurFade inView className="shrink-0">
          <LinkButton href="/business#fleet" variant="outline" showArrow trackSource="home-fleet">
            {t("cta")}
          </LinkButton>
        </BlurFade>
      </div>
    </StorySection>
  );
}
