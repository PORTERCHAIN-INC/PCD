"use client";

import { motion, useReducedMotion, useScroll, useSpring, useTransform } from "framer-motion";
import { useRef } from "react";
import { Building2, Eye, Handshake, Scale, Truck } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import CapacityGuideChat from "@/components/home/CapacityGuideChat";
import Container from "@/components/ui/Container";
import SiteImage from "@/components/ui/SiteImage";
import Magnetic from "@/components/motion/Magnetic";
import MotionReveal, { MotionStagger, MotionStaggerItem } from "@/components/motion/MotionReveal";
import { siteImages } from "@/data/site-images";
import { HUB_FROM } from "@/lib/marketing/config";
import { cardHover, easeOutExpo, springSnappy, staggerContainer, fadeUp } from "@/lib/motion";
import { ANALYTICS_EVENTS, track } from "@/lib/seo/analytics";

const WHY_KEYS = ["scale", "care", "visibility"] as const;
const WHY_ICONS = {
  scale: Scale,
  care: Handshake,
  visibility: Eye,
} as const;

export default function HomeChooser() {
  const t = useTranslations("homeChooser");
  const reduce = useReducedMotion();
  const heroRef = useRef<HTMLElement>(null);
  const fleet = siteImages.hero.welcome;

  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  });
  const imageY = useSpring(useTransform(scrollYProgress, [0, 1], [0, reduce ? 0 : 80]), {
    stiffness: 80,
    damping: 28,
  });
  const imageScale = useTransform(scrollYProgress, [0, 1], [1, reduce ? 1 : 1.06]);

  function trackChoose(from: string, label: string) {
    track(ANALYTICS_EVENTS.CTA_CLICK, {
      sourceSection: "home-chooser",
      from,
      cta_label: label,
    });
  }

  return (
    <>
      <section
        ref={heroRef}
        className="relative min-h-[calc(100dvh-var(--nav-height))] overflow-hidden bg-primary"
      >
        <motion.div
          className="absolute inset-0"
          style={{ y: imageY, scale: imageScale }}
          aria-hidden
        >
          <SiteImage
            image={fleet}
            fill
            priority
            unoptimized
            className="object-cover object-[center_40%]"
            sizes="100vw"
          />
          <div className="absolute inset-0 bg-gradient-to-br from-primary via-primary/88 to-primary/55" />
          <div className="absolute inset-0 bg-gradient-to-t from-primary via-primary/40 to-transparent" />
          {!reduce ? (
            <motion.div
              className="pointer-events-none absolute -right-1/4 top-1/3 h-[45vmax] w-[45vmax] rounded-full bg-secondary/15 blur-3xl"
              animate={{ x: [0, -30, 0], opacity: [0.2, 0.35, 0.2] }}
              transition={{ duration: 16, repeat: Infinity, ease: "easeInOut" }}
            />
          ) : null}
        </motion.div>

        <Container className="relative z-10 grid min-h-[calc(100dvh-var(--nav-height))] items-center gap-10 py-10 pt-[calc(var(--nav-height)+1.25rem)] lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] lg:gap-12 lg:py-14">
          <motion.div
            className="max-w-xl"
            initial={reduce ? false : "hidden"}
            animate="visible"
            variants={staggerContainer}
          >
            <motion.p
              variants={fadeUp}
              transition={{ duration: 0.7, ease: easeOutExpo }}
              className="pc-eyebrow text-accent"
            >
              {t("eyebrow")}
            </motion.p>
            <motion.h1
              variants={fadeUp}
              transition={{ duration: 0.75, ease: easeOutExpo }}
              className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl lg:text-[2.65rem] lg:leading-[1.12]"
            >
              {t("headline")}
            </motion.h1>
            <motion.p
              variants={fadeUp}
              transition={{ duration: 0.7, ease: easeOutExpo }}
              className="mt-4 max-w-md text-base leading-relaxed text-white/75 sm:text-lg"
            >
              {t("subtitle")}
            </motion.p>
            <motion.p
              variants={fadeUp}
              transition={{ duration: 0.65, ease: easeOutExpo }}
              className="mt-3 text-sm text-white/50"
            >
              {t("trustLine")}
            </motion.p>

            <motion.div
              variants={fadeUp}
              transition={{ duration: 0.65, ease: easeOutExpo }}
              className="mt-8 flex flex-wrap gap-3"
            >
              <Link
                href={`/business?from=${HUB_FROM.chooser}`}
                onClick={() => trackChoose(HUB_FROM.chooser, "merchants")}
                className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/8 px-4 py-2.5 text-sm font-semibold text-white backdrop-blur-sm transition-colors hover:bg-white/14"
              >
                <Building2 className="h-4 w-4 text-accent" aria-hidden />
                {t("merchants.cta")}
              </Link>
              <Link
                href={`/vehicle-partner?from=${HUB_FROM.chooser}`}
                onClick={() => trackChoose(HUB_FROM.chooser, "drivers")}
                className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/8 px-4 py-2.5 text-sm font-semibold text-white backdrop-blur-sm transition-colors hover:bg-white/14"
              >
                <Truck className="h-4 w-4 text-accent" aria-hidden />
                {t("drivers.cta")}
              </Link>
            </motion.div>
          </motion.div>

          <motion.div
            initial={reduce ? false : { opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: reduce ? 0 : 0.15, ease: easeOutExpo }}
            className="w-full max-w-xl justify-self-end lg:max-w-none"
          >
            <CapacityGuideChat />
          </motion.div>
        </Container>
      </section>

      <section
        className="border-y border-primary/6 bg-[#F4F6FA]"
        aria-labelledby="home-why-heading"
      >
        <Container className="py-12 sm:py-16">
          <MotionReveal>
            <p className="pc-eyebrow text-secondary">{t("why.eyebrow")}</p>
            <h2
              id="home-why-heading"
              className="mt-2 max-w-2xl text-2xl font-semibold tracking-tight text-primary sm:text-3xl"
            >
              {t("why.title")}
            </h2>
          </MotionReveal>
          <MotionStagger className="mt-8 grid gap-5 sm:grid-cols-3" delay={0.12}>
            {WHY_KEYS.map((key) => {
              const Icon = WHY_ICONS[key];
              return (
                <MotionStaggerItem key={key}>
                  <motion.div
                    className="h-full rounded-2xl border border-primary/8 bg-white p-5 sm:p-6"
                    initial="rest"
                    whileHover={reduce ? undefined : "hover"}
                    variants={cardHover}
                    transition={springSnappy}
                  >
                    <motion.span
                      className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary/10 text-secondary"
                      whileHover={reduce ? undefined : { rotate: -6, scale: 1.06 }}
                      transition={springSnappy}
                    >
                      <Icon className="h-5 w-5" aria-hidden />
                    </motion.span>
                    <h3 className="mt-4 text-base font-semibold text-primary">
                      {t(`why.${key}.title`)}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-muted">
                      {t(`why.${key}.body`)}
                    </p>
                  </motion.div>
                </MotionStaggerItem>
              );
            })}
          </MotionStagger>
        </Container>
      </section>

      <section className="bg-white" aria-labelledby="home-serve-heading">
        <Container className="py-12 sm:py-14">
          <MotionReveal className="mx-auto max-w-3xl text-center">
            <p className="pc-eyebrow text-secondary">{t("serve.eyebrow")}</p>
            <h2
              id="home-serve-heading"
              className="mt-2 text-2xl font-semibold tracking-tight text-primary sm:text-3xl"
            >
              {t("serve.title")}
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-muted sm:text-base">
              {t("serve.industries")}
            </p>
            <p className="mt-3 text-sm leading-relaxed text-muted sm:text-base">
              {t("serve.pricing")}
            </p>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
              <Link
                href={`/business?from=${HUB_FROM.chooser}#industries`}
                onClick={() => trackChoose(HUB_FROM.chooser, "industries")}
                className="text-sm font-semibold text-secondary hover:underline"
              >
                {t("serve.industriesCta")} →
              </Link>
              <span className="text-muted/40" aria-hidden>
                ·
              </span>
              <Link
                href={`/business?from=${HUB_FROM.chooser}#pricing`}
                onClick={() => trackChoose(HUB_FROM.chooser, "pricing")}
                className="text-sm font-semibold text-secondary hover:underline"
              >
                {t("serve.pricingCta")} →
              </Link>
            </div>
          </MotionReveal>
        </Container>
      </section>

      <section className="relative overflow-hidden bg-primary" aria-labelledby="home-ready-heading">
        {!reduce ? (
          <motion.div
            className="pointer-events-none absolute -right-20 top-0 h-64 w-64 rounded-full bg-secondary/25 blur-3xl"
            animate={{ opacity: [0.3, 0.55, 0.3], scale: [1, 1.15, 1] }}
            transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
            aria-hidden
          />
        ) : null}
        <Container className="relative flex flex-col items-start gap-6 py-12 sm:flex-row sm:items-center sm:justify-between sm:py-14">
          <MotionReveal className="max-w-xl">
            <h2
              id="home-ready-heading"
              className="text-2xl font-semibold tracking-tight text-white sm:text-3xl"
            >
              {t("ready.title")}
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-white/65 sm:text-base">
              {t("ready.body")}
            </p>
          </MotionReveal>
          <Magnetic>
            <motion.div
              whileHover={reduce ? undefined : { scale: 1.03 }}
              whileTap={{ scale: 0.98 }}
            >
              <Link
                href={`/contact?intent=quote&from=${HUB_FROM.chooser}`}
                onClick={() => trackChoose(HUB_FROM.chooser, "quote")}
                className="inline-flex shrink-0 items-center justify-center rounded-xl bg-secondary px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-secondary/30 transition-colors hover:bg-[#1d4ed8]"
              >
                {t("ready.cta")}
              </Link>
            </motion.div>
          </Magnetic>
        </Container>
      </section>
    </>
  );
}
