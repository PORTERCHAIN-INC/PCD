"use client";

/**
 * Marketing hero implementation. Prefer importing
 * `@/components/marketing/MarketingHero` from page views.
 */
import { motion, useReducedMotion } from "framer-motion";
import Container from "@/components/ui/Container";
import LinkButton from "@/components/corporate/ui/LinkButton";
import Magnetic from "@/components/motion/Magnetic";
import { cn } from "@/lib/utils";
import { easeOutExpo } from "@/lib/motion";
import { publicEnv } from "@/lib/env";

interface HeroSectionProps {
  badge: string;
  title: string;
  subtitle: string;
  primaryCta: string;
  primaryHref: string;
  secondaryCta?: string;
  secondaryHref?: string;
  variant?: "dark-split" | "light-centered" | "minimal" | "contact-split";
  illustration?: React.ReactNode;
  className?: string;
  trackSource?: string;
  /** Clear fixed navbar when this hero is the first page content (no breadcrumbs above). */
  clearNav?: boolean;
}

function useHeroMotion() {
  const reduce = useReducedMotion();
  return {
    reduce,
    initial: reduce ? false : { opacity: 0, y: 24 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: reduce ? 0.15 : 0.7, ease: easeOutExpo },
  };
}

export default function HeroSection({
  badge,
  title,
  subtitle,
  primaryCta,
  primaryHref,
  secondaryCta,
  secondaryHref,
  variant = "dark-split",
  illustration,
  className,
  trackSource,
  clearNav = false,
}: HeroSectionProps) {
  const m = useHeroMotion();

  if (variant === "light-centered") {
    return (
      <section
        className={cn(
          "bg-gray-bg grid-pattern",
          clearNav ? "pt-24 pb-12 md:pt-28 md:pb-16" : "pt-8 pb-12 md:pt-10 md:pb-14",
          className
        )}
      >
        <Container>
          <motion.div
            initial={m.initial}
            animate={m.animate}
            transition={m.transition}
            className="max-w-3xl mx-auto text-center"
          >
            <span className="inline-flex items-center px-3 py-1 rounded-full bg-secondary/10 text-secondary text-xs font-semibold tracking-wide uppercase">
              {badge}
            </span>
            <h1 className="mt-5 text-3xl sm:text-4xl lg:text-[2.75rem] font-semibold text-primary tracking-tight text-balance leading-[1.1]">
              {title}
            </h1>
            <p className="mt-4 text-base sm:text-lg text-muted leading-relaxed max-w-2xl mx-auto">
              {subtitle}
            </p>
            <div className="mt-7 flex flex-col sm:flex-row items-center justify-center gap-3">
              <Magnetic>
                <LinkButton
                  href={primaryHref}
                  size="lg"
                  trackLabel={primaryCta}
                  trackSource={trackSource}
                >
                  {primaryCta}
                </LinkButton>
              </Magnetic>
              {secondaryCta && secondaryHref && (
                <LinkButton
                  href={secondaryHref}
                  variant="outline"
                  size="lg"
                  trackLabel={secondaryCta}
                  trackSource={trackSource}
                >
                  {secondaryCta}
                </LinkButton>
              )}
            </div>
          </motion.div>
          {illustration && (
            <motion.div
              initial={m.initial}
              animate={m.animate}
              transition={{ ...m.transition, delay: m.reduce ? 0 : 0.12 }}
              className="mt-10 max-w-5xl mx-auto"
            >
              {illustration}
            </motion.div>
          )}
        </Container>
      </section>
    );
  }

  if (variant === "minimal") {
    return (
      <section
        className={cn(
          "bg-white",
          clearNav ? "pt-24 pb-12 md:pt-28 md:pb-16" : "pt-8 pb-12 md:pt-10 md:pb-14",
          className
        )}
      >
        <Container size="narrow">
          <motion.div initial={m.initial} animate={m.animate} transition={m.transition}>
            <span className="text-xs font-semibold text-secondary uppercase tracking-wider">
              {badge}
            </span>
            <h1 className="mt-3 text-3xl sm:text-4xl lg:text-[2.75rem] font-semibold text-primary tracking-tight text-balance leading-[1.1]">
              {title}
            </h1>
            <p className="mt-4 text-base sm:text-lg text-muted leading-relaxed">{subtitle}</p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Magnetic>
                <LinkButton href={primaryHref} trackLabel={primaryCta} trackSource={trackSource}>
                  {primaryCta}
                </LinkButton>
              </Magnetic>
              {secondaryCta && secondaryHref && (
                <LinkButton
                  href={secondaryHref}
                  variant="outline"
                  trackLabel={secondaryCta}
                  trackSource={trackSource}
                >
                  {secondaryCta}
                </LinkButton>
              )}
            </div>
          </motion.div>
        </Container>
      </section>
    );
  }

  if (variant === "contact-split") {
    return (
      <section className={cn("pt-24 pb-10 md:pt-28 md:pb-14 bg-gray-bg", className)}>
        <Container>
          <div className="grid lg:grid-cols-2 gap-10 lg:gap-14 items-start">
            <motion.div initial={m.initial} animate={m.animate} transition={m.transition}>
              <span className="text-xs font-semibold text-secondary uppercase tracking-wider">
                {badge}
              </span>
              <h1 className="mt-4 text-3xl sm:text-4xl lg:text-5xl font-semibold text-primary tracking-tight text-balance leading-[1.1]">
                {title}
              </h1>
              <p className="mt-4 text-muted leading-relaxed">{subtitle}</p>
              <div className="mt-7 flex flex-wrap gap-3">
                <LinkButton
                  href={`mailto:${publicEnv.contactEmail}`}
                  external
                  trackEvent="email_click"
                  trackLabel={primaryCta}
                  trackSource={trackSource ?? "contact_hero"}
                >
                  {primaryCta}
                </LinkButton>
                {secondaryCta && (
                  <LinkButton
                    href="tel:+16476197951"
                    variant="outline"
                    external
                    trackEvent="phone_click"
                    trackLabel={secondaryCta}
                    trackSource={trackSource ?? "contact_hero"}
                  >
                    {secondaryCta}
                  </LinkButton>
                )}
              </div>
            </motion.div>
            {illustration && (
              <motion.div
                initial={m.initial}
                animate={m.animate}
                transition={{ ...m.transition, delay: m.reduce ? 0 : 0.1 }}
              >
                {illustration}
              </motion.div>
            )}
          </div>
        </Container>
      </section>
    );
  }

  return (
    <section
      className={cn(
        "relative min-h-[72vh] flex items-center pt-24 pb-14 overflow-hidden bg-primary",
        className
      )}
    >
      <div className="absolute inset-0 dot-pattern opacity-30 pointer-events-none" aria-hidden />
      {!m.reduce ? (
        <motion.div
          className="absolute top-1/4 -right-32 w-[500px] h-[500px] rounded-full bg-secondary/10 blur-3xl pointer-events-none"
          animate={{ opacity: [0.35, 0.55, 0.35], scale: [1, 1.08, 1] }}
          transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
          aria-hidden
        />
      ) : (
        <div
          className="absolute top-1/4 -right-32 w-[500px] h-[500px] rounded-full bg-secondary/10 blur-3xl pointer-events-none"
          aria-hidden
        />
      )}
      <Container className="relative z-10">
        <div className="grid lg:grid-cols-2 gap-10 lg:gap-14 items-center">
          <motion.div initial={m.initial} animate={m.animate} transition={m.transition}>
            <span className="inline-flex items-center px-3 py-1 rounded-full bg-white/10 text-white/90 text-xs font-semibold tracking-wide uppercase border border-white/10">
              {badge}
            </span>
            <h1 className="mt-5 text-4xl sm:text-5xl lg:text-[3.25rem] font-semibold text-white tracking-tight text-balance leading-[1.06]">
              {title}
            </h1>
            <p className="mt-4 text-lg text-white/65 leading-relaxed max-w-xl">{subtitle}</p>
            <div className="mt-7 flex flex-col sm:flex-row gap-3">
              <Magnetic>
                <LinkButton
                  href={primaryHref}
                  size="lg"
                  trackLabel={primaryCta}
                  trackSource={trackSource}
                >
                  {primaryCta}
                </LinkButton>
              </Magnetic>
              {secondaryCta && secondaryHref && (
                <LinkButton
                  href={secondaryHref}
                  variant="outlineOnDark"
                  size="lg"
                  trackLabel={secondaryCta}
                  trackSource={trackSource}
                >
                  {secondaryCta}
                </LinkButton>
              )}
            </div>
          </motion.div>
          {illustration && (
            <motion.div
              initial={m.reduce ? false : { opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ ...m.transition, delay: m.reduce ? 0 : 0.12 }}
              className="relative"
            >
              {illustration}
            </motion.div>
          )}
        </div>
      </Container>
    </section>
  );
}
