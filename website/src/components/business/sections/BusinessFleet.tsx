"use client";

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import StorySection from "@/components/home/story/StorySection";

const FleetSelector = dynamic(() => import("@/components/shared/FleetSelector"), {
  loading: () => (
    <div
      className="fleet-fit__stage rounded-2xl border border-primary/8 bg-white animate-pulse"
      aria-hidden
    />
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
      fitViewport
    >
      <FleetSelector detailed />
    </StorySection>
  );
}
