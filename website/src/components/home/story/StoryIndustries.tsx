"use client";

import { useTranslations } from "next-intl";
import { ArrowRight } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { industries } from "@/data/industries";
import { HOME_INDUSTRY_TO_NICHE_SLUG } from "@/lib/seo/industry-home-links";
import LinkButton from "@/components/corporate/ui/LinkButton";
import MagicCard from "@/components/magic/magic-card";
import BlurFade from "@/components/magic/blur-fade";
import StorySection from "./StorySection";

const FEATURED_IDS = [
  "construction",
  "electrical",
  "manufacturing",
  "medical",
  "retail",
  "pharmacy",
  "wholesale",
  "ecommerce",
] as const;

export default function StoryIndustries() {
  const t = useTranslations("corporate.home.story.industries");
  const tInd = useTranslations("industries");

  return (
    <StorySection
      id="industries"
      label={t("label")}
      title={t("title")}
      className="bg-gray-bg grid-pattern"
      tight
    >
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {FEATURED_IDS.map((id, i) => {
          const industry = industries.find((item) => item.id === id);
          const Icon = industry?.icon;
          const nicheSlug = HOME_INDUSTRY_TO_NICHE_SLUG[id];
          const href = nicheSlug ? `/industry/${nicheSlug}` : "/business#industries";
          return (
            <BlurFade key={id} delay={i * 0.03} inView>
              <Link href={href} className="block h-full">
                <MagicCard className="h-full px-4 py-4 hover:border-secondary/25">
                  <div className="flex items-center gap-3">
                    {Icon && (
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-secondary/10 text-secondary">
                        <Icon className="h-4 w-4" aria-hidden />
                      </span>
                    )}
                    <span className="text-sm font-semibold text-primary group-hover:text-secondary transition-colors">
                      {tInd(`items.${id}.name`)}
                    </span>
                  </div>
                </MagicCard>
              </Link>
            </BlurFade>
          );
        })}
      </div>
      <BlurFade inView className="mt-8 flex items-center gap-4">
        <LinkButton href="/business#industries" variant="outline" trackSource="home-industries">
          {t("cta")}
        </LinkButton>
        <Link
          href="/business#industries"
          className="inline-flex items-center gap-1 text-sm font-semibold text-secondary hover:underline"
        >
          {t("viewAll")}
          <ArrowRight className="h-4 w-4" />
        </Link>
      </BlurFade>
    </StorySection>
  );
}
