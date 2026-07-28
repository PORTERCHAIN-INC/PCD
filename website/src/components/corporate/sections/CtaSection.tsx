"use client";

import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import Container from "@/components/ui/Container";
import LinkButton from "@/components/corporate/ui/LinkButton";
import FadeIn from "@/components/corporate/motion/FadeIn";
import Magnetic from "@/components/motion/Magnetic";

interface CtaSectionProps {
  title: string;
  subtitle?: string;
  primaryLabel: string;
  primaryHref: string;
  secondaryLabel?: string;
  secondaryHref?: string;
  variant?: "light" | "dark" | "gradient";
  className?: string;
  trackSource?: string;
}

export default function CtaSection({
  title,
  subtitle,
  primaryLabel,
  primaryHref,
  secondaryLabel,
  secondaryHref,
  variant = "dark",
  className,
  trackSource,
}: CtaSectionProps) {
  const isDark = variant === "dark" || variant === "gradient";
  const reduce = useReducedMotion();

  return (
    <section
      className={cn(
        "site-section",
        variant === "light" && "bg-gray-bg",
        variant === "dark" && "bg-primary",
        variant === "gradient" && "bg-primary relative overflow-hidden",
        className
      )}
    >
      {variant === "gradient" && (
        <div className="absolute inset-0 dot-pattern opacity-40 pointer-events-none" aria-hidden />
      )}
      {!reduce && isDark ? (
        <motion.div
          className="pointer-events-none absolute -left-16 top-1/2 h-56 w-56 -translate-y-1/2 rounded-full bg-secondary/25 blur-3xl"
          animate={{ opacity: [0.25, 0.5, 0.25], x: [0, 24, 0] }}
          transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
          aria-hidden
        />
      ) : null}
      <Container className="relative">
        <FadeIn>
          <div className="max-w-3xl mx-auto text-center">
            <h2
              className={cn(
                "text-3xl sm:text-4xl font-semibold tracking-tight text-balance",
                isDark ? "text-white" : "text-primary"
              )}
            >
              {title}
            </h2>
            {subtitle && (
              <p
                className={cn(
                  "mt-3 text-base sm:text-lg leading-relaxed max-w-2xl mx-auto",
                  isDark ? "text-white/65" : "text-muted"
                )}
              >
                {subtitle}
              </p>
            )}
            <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3">
              <Magnetic>
                <motion.div
                  whileHover={reduce ? undefined : { scale: 1.03 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <LinkButton
                    href={primaryHref}
                    variant="primary"
                    size="lg"
                    trackLabel={primaryLabel}
                    trackSource={trackSource}
                  >
                    {primaryLabel}
                  </LinkButton>
                </motion.div>
              </Magnetic>
              {secondaryLabel && secondaryHref && (
                <motion.div
                  whileHover={reduce ? undefined : { scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <LinkButton
                    href={secondaryHref}
                    variant={isDark ? "outlineOnDark" : "outline"}
                    size="lg"
                    trackLabel={secondaryLabel}
                    trackSource={trackSource}
                  >
                    {secondaryLabel}
                  </LinkButton>
                </motion.div>
              )}
            </div>
          </div>
        </FadeIn>
      </Container>
    </section>
  );
}
