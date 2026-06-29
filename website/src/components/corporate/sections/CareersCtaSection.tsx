import Container from "@/components/ui/Container";
import LinkButton from "@/components/corporate/ui/LinkButton";
import FadeIn from "@/components/corporate/motion/FadeIn";
import { CAREERS_APPLY_EMAIL } from "@/data/careers";

interface CareersCtaSectionProps {
  title: string;
  subtitle: string;
  primaryLabel: string;
  secondaryLabel: string;
}

export default function CareersCtaSection({
  title,
  subtitle,
  primaryLabel,
  secondaryLabel,
}: CareersCtaSectionProps) {
  return (
    <section className="site-section bg-primary relative overflow-hidden">
      <div className="absolute inset-0 dot-pattern opacity-20 pointer-events-none" aria-hidden />
      <div
        className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] rounded-full bg-secondary/20 blur-3xl pointer-events-none"
        aria-hidden
      />
      <Container className="relative">
        <FadeIn>
          <div className="max-w-3xl mx-auto text-center py-4 md:py-8">
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-semibold text-white tracking-tight text-balance leading-[1.1]">
              {title}
            </h2>
            <p className="mt-5 text-lg text-white/65 leading-relaxed max-w-xl mx-auto">{subtitle}</p>
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              <a
                href={`mailto:${CAREERS_APPLY_EMAIL}?subject=General%20Application`}
                className="inline-flex items-center justify-center px-10 py-4 rounded-full bg-white text-primary font-semibold text-base hover:bg-gray-bg transition-colors shadow-xl"
              >
                {primaryLabel}
              </a>
              <LinkButton
                href="/contact"
                variant="outline"
                size="lg"
                className="border-white/30 text-white hover:bg-white/10 px-10"
              >
                {secondaryLabel}
              </LinkButton>
            </div>
          </div>
        </FadeIn>
      </Container>
    </section>
  );
}
