"use client";

import { motion } from "framer-motion";
import Container from "@/components/ui/Container";
import LinkButton from "@/components/corporate/ui/LinkButton";
import { cn } from "@/lib/utils";

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
}: HeroSectionProps) {
  if (variant === "light-centered") {
    return (
      <section className={cn("pt-28 pb-20 md:pt-36 md:pb-28 bg-gray-bg grid-pattern", className)}>
        <Container>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="max-w-3xl mx-auto text-center"
          >
            <span className="inline-flex items-center px-3 py-1 rounded-full bg-secondary/10 text-secondary text-xs font-semibold tracking-wide uppercase">
              {badge}
            </span>
            <h1 className="mt-6 text-4xl sm:text-5xl lg:text-[3.25rem] font-semibold text-primary tracking-tight text-balance leading-[1.08]">
              {title}
            </h1>
            <p className="mt-5 text-lg text-muted leading-relaxed max-w-2xl mx-auto">{subtitle}</p>
            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
              <LinkButton href={primaryHref} size="lg">
                {primaryCta}
              </LinkButton>
              {secondaryCta && secondaryHref && (
                <LinkButton href={secondaryHref} variant="outline" size="lg">
                  {secondaryCta}
                </LinkButton>
              )}
            </div>
          </motion.div>
          {illustration && (
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.15 }}
              className="mt-16 max-w-5xl mx-auto"
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
      <section className={cn("pt-28 pb-16 md:pt-36 md:pb-20 bg-white", className)}>
        <Container size="narrow">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <span className="text-xs font-semibold text-secondary uppercase tracking-wider">
              {badge}
            </span>
            <h1 className="mt-4 text-4xl sm:text-5xl font-semibold text-primary tracking-tight text-balance leading-[1.1]">
              {title}
            </h1>
            <p className="mt-5 text-lg text-muted leading-relaxed">{subtitle}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <LinkButton href={primaryHref}>{primaryCta}</LinkButton>
              {secondaryCta && secondaryHref && (
                <LinkButton href={secondaryHref} variant="outline">
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
      <section className={cn("pt-24 pb-12 md:pt-32 md:pb-16 bg-gray-bg", className)}>
        <Container>
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-start">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <span className="text-xs font-semibold text-secondary uppercase tracking-wider">
                {badge}
              </span>
              <h1 className="mt-4 text-3xl sm:text-4xl lg:text-5xl font-semibold text-primary tracking-tight text-balance leading-[1.1]">
                {title}
              </h1>
              <p className="mt-5 text-muted leading-relaxed">{subtitle}</p>
              <div className="mt-8 flex flex-wrap gap-3">
                <LinkButton href="mailto:peter@porterchain.com" external>
                  {primaryCta}
                </LinkButton>
                {secondaryCta && (
                  <LinkButton href="tel:+16476197951" variant="outline" external>
                    {secondaryCta}
                  </LinkButton>
                )}
              </div>
            </motion.div>
            {illustration && (
              <motion.div
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.1 }}
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
        "relative min-h-[92vh] flex items-center pt-20 pb-16 overflow-hidden bg-primary",
        className
      )}
    >
      <div className="absolute inset-0 dot-pattern opacity-30 pointer-events-none" aria-hidden />
      <div
        className="absolute top-1/4 -right-32 w-[500px] h-[500px] rounded-full bg-secondary/10 blur-3xl pointer-events-none"
        aria-hidden
      />
      <Container className="relative z-10">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
          >
            <span className="inline-flex items-center px-3 py-1 rounded-full bg-white/10 text-white/90 text-xs font-semibold tracking-wide uppercase border border-white/10">
              {badge}
            </span>
            <h1 className="mt-6 text-4xl sm:text-5xl lg:text-[3.5rem] font-semibold text-white tracking-tight text-balance leading-[1.06]">
              {title}
            </h1>
            <p className="mt-5 text-lg text-white/65 leading-relaxed max-w-xl">{subtitle}</p>
            <div className="mt-8 flex flex-col sm:flex-row gap-3">
              <LinkButton href={primaryHref} size="lg">
                {primaryCta}
              </LinkButton>
              {secondaryCta && secondaryHref && (
                <LinkButton
                  href={secondaryHref}
                  variant="outline"
                  size="lg"
                  className="border-white/30 text-white hover:bg-white/10"
                >
                  {secondaryCta}
                </LinkButton>
              )}
            </div>
          </motion.div>
          {illustration && (
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, delay: 0.12 }}
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
