"use client";

import { useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import LinkButton from "@/components/corporate/ui/LinkButton";
import HeroPhoto from "@/components/ui/HeroPhoto";
import BlurFade from "@/components/magic/blur-fade";
import Magnetic from "@/components/motion/Magnetic";
import { siteImages } from "@/data/site-images";
import { cn } from "@/lib/utils";
import { easeOutExpo, springSnappy, staggerContainer, fadeUp } from "@/lib/motion";
import VehiclePartnerInquiryForm from "@/components/vehicle-partner/VehiclePartnerInquiryForm";
import type { Locale } from "@/i18n/routing";

type Props = {
  locale: Locale;
};

export default function VehiclePartnerHero({ locale }: Props) {
  const t = useTranslations("vehiclePartner");
  const [formActive, setFormActive] = useState(false);
  const reduce = useReducedMotion();
  const contactHref = `/${locale}/contact?from=drivers-hub`;

  return (
    <section
      className={cn(
        "relative pt-24 pb-12 md:pt-28 md:pb-16 bg-gray-bg grid-pattern overflow-hidden",
        formActive && "motion-paused"
      )}
    >
      {!reduce ? (
        <motion.div
          className="pointer-events-none absolute -right-24 top-20 h-72 w-72 rounded-full bg-secondary/15 blur-3xl"
          animate={{ opacity: [0.3, 0.55, 0.3], scale: [1, 1.12, 1] }}
          transition={{ duration: 11, repeat: Infinity, ease: "easeInOut" }}
          aria-hidden
        />
      ) : null}
      <Container className="relative z-10">
        <div className="grid lg:grid-cols-2 gap-10 lg:gap-14 items-start">
          <motion.div
            className="max-w-xl"
            initial={reduce ? false : "hidden"}
            animate="visible"
            variants={staggerContainer}
          >
            <motion.span
              variants={fadeUp}
              transition={{ duration: 0.55, ease: easeOutExpo }}
              className="inline-flex items-center px-3 py-1 rounded-full bg-secondary/10 text-secondary text-xs font-semibold tracking-wide uppercase"
            >
              {t("hero.badge")}
            </motion.span>
            <motion.h1
              variants={fadeUp}
              transition={{ duration: 0.7, ease: easeOutExpo }}
              className="mt-6 text-4xl sm:text-5xl font-semibold text-primary tracking-tight text-balance leading-[1.08]"
            >
              {t("hero.title")}
            </motion.h1>
            <motion.p
              variants={fadeUp}
              transition={{ duration: 0.65, ease: easeOutExpo }}
              className="mt-5 text-lg text-muted leading-relaxed"
            >
              {t("hero.subtitle")}
            </motion.p>
            <motion.div
              variants={fadeUp}
              transition={{ duration: 0.6, ease: easeOutExpo }}
              className="mt-8 flex flex-col sm:flex-row flex-wrap gap-3"
            >
              <Magnetic>
                <LinkButton href="#apply" size="lg" trackSource="vehicle-partner-hero">
                  {t("hero.primaryCta")}
                </LinkButton>
              </Magnetic>
              <LinkButton
                href={contactHref}
                variant="outline"
                size="lg"
                trackSource="vehicle-partner-hero"
              >
                {t("hero.secondaryCta")}
              </LinkButton>
            </motion.div>
            <BlurFade delay={0.2} className="mt-12 max-w-5xl">
              <motion.div
                whileHover={reduce ? undefined : { y: -4 }}
                transition={springSnappy}
                className="overflow-hidden rounded-2xl"
              >
                <HeroPhoto image={siteImages.brand.warehouseDock} priority />
              </motion.div>
            </BlurFade>
          </motion.div>

          <BlurFade delay={0.15} yOffset={24}>
            <VehiclePartnerInquiryForm id="apply" onInteractionChange={setFormActive} />
          </BlurFade>
        </div>
      </Container>
    </section>
  );
}
