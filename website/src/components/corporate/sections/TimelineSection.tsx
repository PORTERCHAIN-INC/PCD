import { cn } from "@/lib/utils";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import FadeIn from "@/components/corporate/motion/FadeIn";

export interface TimelineStep {
  title: string;
  description: string;
}

interface TimelineSectionProps {
  label?: string;
  title: string;
  subtitle?: string;
  steps: TimelineStep[];
  variant?: "horizontal" | "vertical" | "alternating";
  className?: string;
}

export default function TimelineSection({
  label,
  title,
  subtitle,
  steps,
  variant = "horizontal",
  className,
}: TimelineSectionProps) {
  if (variant === "vertical") {
    return (
      <section className={cn("site-section bg-white", className)}>
        <Container>
          <SectionHeader label={label} title={title} subtitle={subtitle} />
          <div className="max-w-2xl mx-auto relative">
            <div className="absolute left-[1.125rem] top-2 bottom-2 w-px bg-gradient-to-b from-secondary via-secondary/30 to-transparent" />
            <ol className="space-y-7">
              {steps.map((step, i) => (
                <FadeIn key={i} as="li" delay={i * 0.08}>
                  <div className="flex gap-4">
                    <div className="relative z-10 w-9 h-9 rounded-full bg-secondary text-white text-sm font-semibold flex items-center justify-center shrink-0 shadow-md shadow-secondary/25">
                      {i + 1}
                    </div>
                    <div className="pt-1">
                      <h3 className="text-lg font-semibold text-primary tracking-tight">
                        {step.title}
                      </h3>
                      <p className="mt-2 text-sm text-muted leading-relaxed">{step.description}</p>
                    </div>
                  </div>
                </FadeIn>
              ))}
            </ol>
          </div>
        </Container>
      </section>
    );
  }

  if (variant === "alternating") {
    return (
      <section className={cn("site-section bg-gray-bg", className)}>
        <Container>
          <SectionHeader label={label} title={title} subtitle={subtitle} />
          <div className="space-y-10 md:space-y-12">
            {steps.map((step, i) => (
              <FadeIn key={i} delay={i * 0.06}>
                <div
                  className={cn(
                    "grid md:grid-cols-2 gap-6 md:gap-10 items-center",
                    i % 2 === 1 && "md:[&>div:first-child]:order-2"
                  )}
                >
                  <div>
                    <span className="text-xs font-semibold text-secondary uppercase tracking-wider">
                      Step {i + 1}
                    </span>
                    <h3 className="mt-2 text-xl font-semibold text-primary tracking-tight">
                      {step.title}
                    </h3>
                    <p className="mt-2 text-muted leading-relaxed">{step.description}</p>
                  </div>
                  <div className="h-40 md:h-48 rounded-2xl bg-white border border-primary/[0.06] grid-pattern flex items-center justify-center">
                    <div className="w-14 h-14 rounded-2xl bg-secondary/10 flex items-center justify-center">
                      <span className="text-xl font-bold text-secondary">{i + 1}</span>
                    </div>
                  </div>
                </div>
              </FadeIn>
            ))}
          </div>
        </Container>
      </section>
    );
  }

  return (
    <section className={cn("site-section bg-gray-bg", className)}>
      <Container>
        <SectionHeader label={label} title={title} subtitle={subtitle} />
        <div className="relative">
          <div className="hidden md:block absolute top-5 left-0 right-0 h-px bg-gradient-to-r from-transparent via-secondary/30 to-transparent" />
          <ol className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 md:gap-6">
            {steps.map((step, i) => (
              <FadeIn key={i} as="li" delay={i * 0.08} className="list-none">
                <div className="relative">
                  <div className="w-10 h-10 rounded-full bg-secondary text-white text-sm font-semibold flex items-center justify-center mb-5 shadow-md shadow-secondary/20 relative z-10">
                    {i + 1}
                  </div>
                  <h3 className="text-base font-semibold text-primary tracking-tight">
                    {step.title}
                  </h3>
                  <p className="mt-2 text-sm text-muted leading-relaxed">{step.description}</p>
                </div>
              </FadeIn>
            ))}
          </ol>
        </div>
      </Container>
    </section>
  );
}
