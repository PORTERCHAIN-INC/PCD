import { cn } from "@/lib/utils";
import Container from "@/components/ui/Container";
import LinkButton from "@/components/corporate/ui/LinkButton";
import FadeIn from "@/components/corporate/motion/FadeIn";

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
                  "mt-4 text-lg leading-relaxed max-w-2xl mx-auto",
                  isDark ? "text-white/65" : "text-muted"
                )}
              >
                {subtitle}
              </p>
            )}
            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
              <LinkButton
                href={primaryHref}
                variant="primary"
                size="lg"
                trackLabel={primaryLabel}
                trackSource={trackSource}
              >
                {primaryLabel}
              </LinkButton>
              {secondaryLabel && secondaryHref && (
                <LinkButton
                  href={secondaryHref}
                  variant={isDark ? "outlineOnDark" : "outline"}
                  size="lg"
                  trackLabel={secondaryLabel}
                  trackSource={trackSource}
                >
                  {secondaryLabel}
                </LinkButton>
              )}
            </div>
          </div>
        </FadeIn>
      </Container>
    </section>
  );
}
