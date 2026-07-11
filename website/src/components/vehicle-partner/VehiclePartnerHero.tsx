"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import LinkButton from "@/components/corporate/ui/LinkButton";
import HeroPhoto from "@/components/ui/HeroPhoto";
import { siteImages } from "@/data/site-images";
import { cn } from "@/lib/utils";
import VehiclePartnerInquiryForm from "@/components/vehicle-partner/VehiclePartnerInquiryForm";
import type { Locale } from "@/i18n/routing";

type Props = {
  locale: Locale;
};

export default function VehiclePartnerHero({ locale }: Props) {
  const t = useTranslations("vehiclePartner");
  const [formActive, setFormActive] = useState(false);
  const contactHref = `/${locale}/contact?from=vehicle-partner`;

  return (
    <section
      className={cn(
        "relative pt-28 pb-16 md:pt-36 md:pb-20 bg-gray-bg grid-pattern overflow-hidden",
        formActive && "motion-paused"
      )}
    >
      <Container className="relative z-10">
        <div className="grid lg:grid-cols-2 gap-10 lg:gap-14 items-start">
          <div className="max-w-xl">
            <span className="inline-flex items-center px-3 py-1 rounded-full bg-secondary/10 text-secondary text-xs font-semibold tracking-wide uppercase">
              {t("hero.badge")}
            </span>
            <h1 className="mt-6 text-4xl sm:text-5xl font-semibold text-primary tracking-tight text-balance leading-[1.08]">
              {t("hero.title")}
            </h1>
            <p className="mt-5 text-lg text-muted leading-relaxed">{t("hero.subtitle")}</p>
            <div className="mt-8 flex flex-col sm:flex-row flex-wrap gap-3">
              <LinkButton href="#apply" size="lg" trackSource="vehicle-partner-hero">
                {t("hero.primaryCta")}
              </LinkButton>
              <LinkButton
                href={contactHref}
                variant="outline"
                size="lg"
                trackSource="vehicle-partner-hero"
              >
                {t("hero.secondaryCta")}
              </LinkButton>
            </div>
            <div className="mt-12 max-w-5xl">
              <HeroPhoto image={siteImages.hero.partner} priority />
            </div>
          </div>

          <VehiclePartnerInquiryForm id="apply" onInteractionChange={setFormActive} />
        </div>
      </Container>
    </section>
  );
}
