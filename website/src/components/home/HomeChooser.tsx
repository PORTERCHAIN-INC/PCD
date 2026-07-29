"use client";

import { motion, useReducedMotion, useScroll, useSpring, useTransform } from "framer-motion";
import { useRef } from "react";
import {
  Bot,
  Building2,
  Check,
  Code2,
  FileCheck2,
  Headphones,
  LayoutDashboard,
  MapPin,
  MessageCircle,
  Package,
  Sparkles,
  Truck,
  Zap,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import CapacityGuideChat from "@/components/home/CapacityGuideChat";
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
import { easeOutExpo, springSnappy, staggerContainer, fadeUp } from "@/lib/motion";
import { ANALYTICS_EVENTS, track } from "@/lib/seo/analytics";
import { cn } from "@/lib/utils";

const CAPABILITY_KEYS = [
  "quotes",
  "book",
  "tracking",
  "pod",
  "dashboard",
  "api",
  "ai",
  "support",
] as const;

const CAPABILITY_ICONS = {
  quotes: Zap,
  book: Package,
  tracking: MapPin,
  pod: FileCheck2,
  dashboard: LayoutDashboard,
  api: Code2,
  ai: Bot,
  support: Headphones,
} as const;

const CONTROL_KEYS = ["quotes", "book", "track", "pod", "reports", "api", "team"] as const;

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

  function trackChoose(label: string) {
    track(ANALYTICS_EVENTS.CTA_CLICK, {
      sourceSection: "home-chooser",
      from: HUB_FROM.chooser,
      cta_label: label,
    });
  }

  const businessHref = `/business?from=${HUB_FROM.chooser}`;

  function openSpecialistChat(label: string) {
    trackChoose(label);
    openLogisticsChat({ scroll: true });
  }

  return (
    <>
      {/* Hero — brand + chat (interactive console stays) */}
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

            <motion.div
              variants={fadeUp}
              transition={{ duration: 0.65, ease: easeOutExpo }}
              className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start"
            >
              <div className="flex flex-col gap-2">
                <Magnetic>
                  <ShimmerButton
                    href={businessHref}
                    trackSource="home-hero-business"
                    showArrow
                    className="rounded-xl"
                  >
                    {t("primaryCta")}
                  </ShimmerButton>
                </Magnetic>
                <p className="max-w-xs text-xs leading-relaxed text-white/45 sm:pl-1">
                  {t("primaryCtaHint")}
                </p>
              </div>
              <button
                type="button"
                onClick={() => openSpecialistChat("specialist")}
                className="inline-flex min-h-[var(--touch-min)] items-center justify-center gap-2 rounded-xl border border-white/20 bg-white/5 px-6 py-3 text-sm font-semibold text-white backdrop-blur-sm transition-colors hover:bg-white/12"
              >
                <MessageCircle className="h-4 w-4 text-accent" aria-hidden />
                {t("secondaryCta")}
              </button>
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
            {/* Quiet depth plate — no looping border/shimmer on the chat */}
            <div
              className="pointer-events-none absolute -inset-3 rounded-[2rem] bg-gradient-to-br from-secondary/25 via-transparent to-accent/10 blur-2xl"
              aria-hidden
            />
            <CapacityGuideChat />
          </motion.div>
        </Container>
      </section>

      {/* Section 2 — capabilities bento */}
      <section className="relative overflow-hidden bg-[#F4F6FA]" aria-labelledby="home-ops-heading">
        <Container className="py-16 sm:py-20">
          <MotionReveal className="mx-auto max-w-2xl text-center">
            <p className="pc-eyebrow text-secondary">{t("ops.eyebrow")}</p>
            <h2
              id="home-ops-heading"
              className="mt-2 text-2xl font-semibold tracking-tight text-primary sm:text-3xl lg:text-4xl"
            >
              {t("ops.title")}
            </h2>
          </MotionReveal>

          <MotionStagger className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-4" delay={0.08}>
            {CAPABILITY_KEYS.map((key, i) => {
              const Icon = CAPABILITY_ICONS[key];
              const featured = i === 0 || i === 7;
              return (
                <MotionStaggerItem key={key}>
                  <MagicCard
                    className={cn(
                      "h-full p-5",
                      featured && "sm:col-span-1 lg:row-span-1 border-secondary/15"
                    )}
                  >
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary/10 text-secondary">
                      <Icon className="h-5 w-5" aria-hidden />
                    </span>
                    <h3 className="mt-4 text-sm font-semibold text-primary sm:text-base">
                      {t(`ops.items.${key}`)}
                    </h3>
                  </MagicCard>
                </MotionStaggerItem>
              );
            })}
          </MotionStagger>
        </Container>
      </section>

      {/* Section 3 — one account control */}
      <section className="bg-white" aria-labelledby="home-control-heading">
        <Container className="py-16 sm:py-20">
          <div className="grid items-center gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:gap-16">
            <MotionReveal>
              <p className="pc-eyebrow text-secondary">{t("control.eyebrow")}</p>
              <h2
                id="home-control-heading"
                className="mt-2 text-2xl font-semibold tracking-tight text-primary sm:text-3xl lg:text-4xl"
              >
                {t("control.title")}
              </h2>
              <p className="mt-4 text-base leading-relaxed text-muted sm:text-lg">
                {t("control.subtitle")}
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <ShimmerButton
                  href={businessHref}
                  trackSource="home-control-business"
                  showArrow
                  className="rounded-xl"
                >
                  {t("primaryCta")}
                </ShimmerButton>
                <button
                  type="button"
                  onClick={() => openSpecialistChat("specialist-control")}
                  className="inline-flex min-h-[var(--touch-min)] items-center justify-center rounded-xl border border-primary/12 bg-white px-5 py-3 text-sm font-semibold text-primary transition-colors hover:border-secondary/30 hover:bg-secondary/5"
                >
                  {t("secondaryCta")}
                </button>
              </div>
            </MotionReveal>

            <MotionStagger className="grid gap-3" delay={0.1}>
              {CONTROL_KEYS.map((key) => (
                <MotionStaggerItem key={key}>
                  <motion.div
                    className="flex items-start gap-3 rounded-2xl border border-primary/6 bg-gray-bg/80 px-4 py-3.5"
                    whileHover={reduce ? undefined : { x: 4 }}
                    transition={springSnappy}
                  >
                    <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-secondary/12 text-secondary">
                      <Check className="h-3.5 w-3.5" strokeWidth={2.5} aria-hidden />
                    </span>
                    <p className="text-sm font-medium leading-relaxed text-primary sm:text-[0.95rem]">
                      {t(`control.items.${key}`)}
                    </p>
                  </motion.div>
                </MotionStaggerItem>
              ))}
            </MotionStagger>
          </div>
        </Container>
      </section>

      {/* Section 4 — pillars */}
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

      {/* Section 5 — industries */}
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

      {/* Final CTA */}
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
                  href={businessHref}
                  trackSource="home-ready-business"
                  showArrow
                  variant="onDark"
                  className="rounded-xl"
                >
                  {t("primaryCta")}
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
