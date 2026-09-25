"use client";

import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import SiteImage from "@/components/ui/SiteImage";
import AnimatedGradientText from "@/components/magic/animated-gradient-text";
import BlurFade from "@/components/magic/blur-fade";
import QuoteSignupPanel from "@/components/marketing/business/QuoteSignupPanel";
import { siteImages } from "@/data/site-images";

/**
 * Business / services hero — Open Road brand photo as full-bleed bg,
 * soft white merge on the left for copy + quote sign-up CTA in front.
 */
export default function BusinessHero() {
  const t = useTranslations("businessPage.hero");
  const openRoad = siteImages.brand.openRoad;

  return (
    <section className="relative isolate min-h-[min(88svh,44rem)] overflow-hidden bg-white">
      <div className="absolute inset-0" aria-hidden>
        <SiteImage
          image={openRoad}
          fill
          priority
          unoptimized
          className="object-cover object-[72%_center] sm:object-[68%_center] lg:object-[62%_center]"
          sizes="100vw"
        />
        <div className="biz-hero-merge pointer-events-none absolute inset-0" />
      </div>

      <Container className="relative z-10 flex min-h-[min(88svh,44rem)] flex-col justify-center pt-[calc(var(--nav-height)+1.5rem)] pb-12 sm:pb-16 lg:pb-20">
        <div className="grid items-center gap-10 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] lg:gap-12 xl:gap-16">
          <div className="max-w-xl">
            <BlurFade>
              <p className="biz-hero-eyebrow">{t("badge")}</p>
            </BlurFade>

            <BlurFade delay={0.06}>
              <h1 className="biz-hero-title mt-4 text-balance text-primary">
                {t("titleLine1")}
                <span className="block">
                  <AnimatedGradientText>{t("titleLine2")}</AnimatedGradientText>
                </span>
              </h1>
            </BlurFade>

            <BlurFade delay={0.12}>
              <p className="biz-hero-subtitle mt-5">{t("subtitle")}</p>
            </BlurFade>
          </div>

          <BlurFade delay={0.18}>
            <QuoteSignupPanel
              id="inquiry"
              variant="hero"
              className="biz-hero-form"
              from="business-hero"
            />
          </BlurFade>
        </div>
      </Container>
    </section>
  );
}
