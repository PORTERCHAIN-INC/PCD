"use client";

import { motion, useReducedMotion, useScroll, useSpring, useTransform } from "framer-motion";
import { useRef } from "react";
import { Building2, Code2, Headphones, LayoutDashboard, Sparkles, Truck } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import CapacityGuideChat from "@/components/marketing/home/CapacityGuideChat";
import HomeVehicleLeadCapture from "@/components/marketing/home/HomeVehicleLeadCapture";
import CapacityOpsShowcase from "@/components/marketing/CapacityOpsShowcase";
import { ProductTrust as CapacityProductTrust } from "@/components/marketing/MarketingProof";
import AnimatedGradientText from "@/components/magic/animated-gradient-text";
import BlurFade from "@/components/magic/blur-fade";
import MagicCard from "@/components/magic/magic-card";
import Marquee from "@/components/magic/marquee";
import ShimmerButton from "@/components/magic/shimmer-button";
import Magnetic from "@/components/motion/Magnetic";
import MotionReveal, { MotionStagger, MotionStaggerItem } from "@/components/motion/MotionReveal";
import Container from "@/components/ui/Container";
import SiteImage from "@/components/ui/SiteImage";
import { siteImages } from "@/data/site-images";
import { HUB_FROM } from "@/lib/marketing/config";
import { openLogisticsChat } from "@/lib/home/open-logistics-chat";
import { easeOutExpo, staggerContainer, fadeUp } from "@/lib/motion";
import { ANALYTICS_EVENTS, track } from "@/lib/seo/analytics";

/**
 * Homepage story (one job per band):
 * 1. Hero — who + outcome + quote path
 * 2. What we do — ops theater
 * 3. Product UI — interactive quote/track/POD
 * 4. Full stack — five layers you buy
 * 5. Industries — who it’s for
 * 6. Final CTA — quote
 * (No success-stories band until permissioned customer proof exists.)
 */

const PILLAR_KEYS = ["transportation", "software", "ai", "operations", "technology"] as const;

const PILLAR_ICONS = {
  transportation: Truck,
  software: LayoutDashboard,
  ai: Sparkles,
  operations: Headphones,
  technology: Code2,
} as const;

const INDUSTRY_KEYS = [
  "manufacturing",
  "construction",
  "industrial",
  "electrical",
  "hvac",
  "plumbing",
  "medical",
  "retail",
  "wholesale",
] as const;

export default function HomeChooser() {
  const t = useTranslations("homeChooser");
  const tCta = useTranslations("common.cta");
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

  function trackChoose(label: string) {
    track(ANALYTICS_EVENTS.CTA_CLICK, {
      sourceSection: "home-chooser",
      from: HUB_FROM.chooser,
      cta_label: label,
    });
  }

  const quoteHref = `/sign-up?intent=quote&from=${HUB_FROM.chooser}`;

  function openSpecialistChat(label: string) {
    trackChoose(label);
    openLogisticsChat({ scroll: true });
  }

  return (
    <>
      {/* 1 — Hero */}
      <section
        ref={heroRef}
        className="relative min-h-[calc(100dvh-var(--nav-height))] overflow-hidden bg-primary"
      >
        <motion.div className="absolute inset-0" style={{ y: imageY }} aria-hidden>
          <SiteImage
            image={fleet}
            fill
            priority
            quality={75}
            className="object-cover object-[center_40%]"
            sizes="100vw"
          />
          <div className="absolute inset-0 bg-gradient-to-br from-primary via-primary/90 to-primary/50" />
          <div className="absolute inset-0 bg-gradient-to-t from-primary via-primary/45 to-transparent" />
          {!reduce ? (
            <motion.div
              className="pointer-events-none absolute -right-1/4 top-1/3 h-[45vmax] w-[45vmax] rounded-full bg-secondary/20 blur-3xl"
              animate={{ x: [0, -30, 0], opacity: [0.22, 0.4, 0.22] }}
              transition={{ duration: 16, repeat: Infinity, ease: "easeInOut" }}
            />
          ) : null}
        </motion.div>

        <Container className="relative z-10 grid min-h-[calc(100dvh-var(--nav-height))] items-center gap-10 py-10 pt-[calc(var(--nav-height)+1.25rem)] lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:gap-12 lg:py-14">
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
              className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl lg:text-[2.75rem] lg:leading-[1.1]"
            >
              {t("headline")}
            </motion.h1>
            <motion.p
              variants={fadeUp}
              transition={{ duration: 0.7, ease: easeOutExpo }}
              className="mt-4 max-w-lg text-base leading-relaxed text-white/75 sm:text-lg"
            >
              {t("subtitle")}
            </motion.p>

            <motion.div variants={fadeUp} transition={{ duration: 0.65, ease: easeOutExpo }}>
              <HomeVehicleLeadCapture />
            </motion.div>

            <motion.p
              variants={fadeUp}
              transition={{ duration: 0.65, ease: easeOutExpo }}
              className="mt-8 max-w-md text-sm leading-relaxed text-white/55"
            >
              {t("trustLine")}
            </motion.p>
          </motion.div>

          <motion.div
            initial={reduce ? false : { opacity: 0, clipPath: "inset(0 0 12% 0)" }}
            animate={{ opacity: 1, clipPath: "inset(0 0 0% 0)" }}
            transition={{ duration: 0.85, delay: reduce ? 0 : 0.2, ease: easeOutExpo }}
            className="relative w-full max-w-xl justify-self-end lg:max-w-none"
          >
            <div
              className="pointer-events-none absolute -inset-3 rounded-[2rem] bg-gradient-to-br from-secondary/25 via-transparent to-accent/10 blur-2xl"
              aria-hidden
            />
            <CapacityGuideChat />
          </motion.div>
        </Container>
      </section>

      {/* 2 — What we do · 3 — Interactive product UI */}
      <CapacityOpsShowcase from={HUB_FROM.chooser} />
      <CapacityProductTrust from={HUB_FROM.chooser} tone="light" />

      {/* 4 — Full stack */}
      <section
        className="relative overflow-hidden border-y border-primary/6 bg-[#F4F6FA]"
        aria-labelledby="home-pillars-heading"
      >
        {!reduce ? (
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.35]"
            style={{
              backgroundImage:
                "radial-gradient(circle at 20% 20%, rgba(37,99,235,0.12), transparent 42%), radial-gradient(circle at 80% 60%, rgba(59,130,246,0.1), transparent 40%)",
            }}
            aria-hidden
          />
        ) : null}
        <Container className="relative py-16 sm:py-20">
          <MotionReveal className="mx-auto max-w-2xl text-center">
            <p className="pc-eyebrow text-secondary">{t("pillars.eyebrow")}</p>
            <h2
              id="home-pillars-heading"
              className="mt-2 text-2xl font-semibold tracking-tight text-primary sm:text-3xl lg:text-4xl"
            >
              {t("pillars.title")}
            </h2>
            <p className="mt-4 text-base leading-relaxed text-muted">{t("pillars.subtitle")}</p>
          </MotionReveal>

          <MotionStagger
            className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5"
            delay={0.1}
          >
            {PILLAR_KEYS.map((key) => {
              const Icon = PILLAR_ICONS[key];
              return (
                <MotionStaggerItem key={key}>
                  <MagicCard className="h-full p-5 sm:p-6">
                    <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary text-white shadow-lg shadow-primary/20">
                      <Icon className="h-5 w-5" aria-hidden />
                    </span>
                    <h3 className="mt-4 text-base font-semibold text-primary">
                      {t(`pillars.${key}.title`)}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-muted">
                      {t(`pillars.${key}.body`)}
                    </p>
                  </MagicCard>
                </MotionStaggerItem>
              );
            })}
          </MotionStagger>
        </Container>
      </section>

      {/* 5 — Industries */}
      <section className="bg-white" aria-labelledby="home-industries-heading">
        <Container className="py-16 sm:py-20">
          <MotionReveal className="mx-auto max-w-2xl text-center">
            <p className="pc-eyebrow text-secondary">{t("industries.eyebrow")}</p>
            <h2
              id="home-industries-heading"
              className="mt-2 text-2xl font-semibold tracking-tight text-primary sm:text-3xl lg:text-4xl"
            >
              {t("industries.title")}
            </h2>
            <p className="mt-4 text-base leading-relaxed text-muted">{t("industries.subtitle")}</p>
          </MotionReveal>

          <BlurFade delay={0.12} inView className="mt-10">
            <Marquee speed="slow" className="py-2">
              {INDUSTRY_KEYS.map((key) => (
                <span
                  key={key}
                  className="inline-flex items-center gap-2 rounded-full border border-primary/8 bg-gray-bg px-5 py-2.5 text-sm font-semibold text-primary"
                >
                  <Building2 className="h-3.5 w-3.5 text-secondary" aria-hidden />
                  {t(`industries.items.${key}`)}
                </span>
              ))}
            </Marquee>
          </BlurFade>

          <MotionReveal delay={0.15} className="mt-10 text-center">
            <p className="text-sm font-medium text-muted sm:text-base">{t("industries.closing")}</p>
            <Link
              href={`/business?from=${HUB_FROM.chooser}#industries`}
              onClick={() => trackChoose("industries")}
              className="mt-4 inline-flex text-sm font-semibold text-secondary hover:underline"
            >
              {t("industries.cta")} →
            </Link>
          </MotionReveal>
        </Container>
      </section>

      {/* 6 — Final CTA */}
      <section className="relative overflow-hidden bg-primary" aria-labelledby="home-ready-heading">
        {!reduce ? (
          <>
            <motion.div
              className="pointer-events-none absolute -left-24 top-0 h-72 w-72 rounded-full bg-secondary/30 blur-3xl"
              animate={{ opacity: [0.25, 0.5, 0.25], scale: [1, 1.12, 1] }}
              transition={{ duration: 9, repeat: Infinity, ease: "easeInOut" }}
              aria-hidden
            />
            <motion.div
              className="pointer-events-none absolute -right-16 bottom-0 h-64 w-64 rounded-full bg-accent/25 blur-3xl"
              animate={{ opacity: [0.2, 0.45, 0.2] }}
              transition={{ duration: 11, repeat: Infinity, ease: "easeInOut" }}
              aria-hidden
            />
          </>
        ) : null}
        <Container className="relative py-16 sm:py-20">
          <MotionReveal className="mx-auto max-w-2xl text-center">
            <h2
              id="home-ready-heading"
              className="text-2xl font-semibold tracking-tight text-white sm:text-3xl lg:text-4xl"
            >
              {t("ready.title")}
            </h2>
            <p className="mt-4 text-base leading-relaxed text-white/65 sm:text-lg">
              {t("ready.body")}{" "}
              <AnimatedGradientText className="font-semibold">
                {t("ready.highlight")}
              </AnimatedGradientText>
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Magnetic>
                <ShimmerButton
                  href={quoteHref}
                  trackSource="home-ready-quote"
                  showArrow
                  variant="onDark"
                  className="rounded-xl"
                >
                  {tCta("quote")}
                </ShimmerButton>
              </Magnetic>
              <button
                type="button"
                onClick={() => openSpecialistChat("specialist-ready")}
                className="inline-flex min-h-[var(--touch-min)] items-center justify-center rounded-xl border border-white/20 bg-white/5 px-6 py-3 text-sm font-semibold text-white backdrop-blur-sm transition-colors hover:bg-white/12"
              >
                {t("ready.secondaryCta")}
              </button>
            </div>
          </MotionReveal>
        </Container>
      </section>
    </>
  );
}
