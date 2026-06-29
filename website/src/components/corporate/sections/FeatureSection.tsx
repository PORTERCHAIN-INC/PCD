import { cn } from "@/lib/utils";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import FadeIn from "@/components/corporate/motion/FadeIn";
import type { LucideIcon } from "lucide-react";

export interface FeatureItem {
  title: string;
  description: string;
  icon?: LucideIcon;
}

interface FeatureSectionProps {
  label?: string;
  title: string;
  subtitle?: string;
  items: FeatureItem[];
  variant?: "grid" | "rows" | "pillars";
  className?: string;
  id?: string;
}

export default function FeatureSection({
  label,
  title,
  subtitle,
  items,
  variant = "grid",
  className,
  id,
}: FeatureSectionProps) {
  if (variant === "rows") {
    return (
      <section id={id} className={cn("site-section bg-white", className)}>
        <Container>
          <SectionHeader label={label} title={title} subtitle={subtitle} align="left" className="max-w-2xl" />
          <div className="space-y-6 mt-12">
            {items.map((item, i) => (
              <FadeIn key={i} delay={i * 0.06}>
                <div className="grid md:grid-cols-[1fr_2fr] gap-4 md:gap-12 py-8 border-b border-primary/[0.06] last:border-0">
                  <h3 className="text-lg font-semibold text-primary tracking-tight">{item.title}</h3>
                  <p className="text-muted leading-relaxed">{item.description}</p>
                </div>
              </FadeIn>
            ))}
          </div>
        </Container>
      </section>
    );
  }

  if (variant === "pillars") {
    return (
      <section id={id} className={cn("site-section bg-primary text-white", className)}>
        <Container>
          <SectionHeader label={label} title={title} subtitle={subtitle} dark />
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {items.map((item, i) => (
              <FadeIn key={i} delay={i * 0.08}>
                <div className="p-6 rounded-2xl bg-white/[0.04] border border-white/[0.08] h-full">
                  {item.icon && (
                    <item.icon className="w-5 h-5 text-secondary mb-4" aria-hidden />
                  )}
                  <h3 className="text-base font-semibold tracking-tight">{item.title}</h3>
                  <p className="mt-2 text-sm text-white/60 leading-relaxed">{item.description}</p>
                </div>
              </FadeIn>
            ))}
          </div>
        </Container>
      </section>
    );
  }

  return (
    <section id={id} className={cn("site-section bg-white", className)}>
      <Container>
        <SectionHeader label={label} title={title} subtitle={subtitle} />
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {items.map((item, i) => (
            <FadeIn key={i} delay={i * 0.06}>
              <div className="card-surface card-surface-hover p-6 h-full">
                {item.icon && (
                  <div className="w-10 h-10 rounded-xl bg-secondary/10 flex items-center justify-center mb-4">
                    <item.icon className="w-5 h-5 text-secondary" aria-hidden />
                  </div>
                )}
                <h3 className="text-base font-semibold text-primary tracking-tight">{item.title}</h3>
                <p className="mt-2 text-sm text-muted leading-relaxed">{item.description}</p>
              </div>
            </FadeIn>
          ))}
        </div>
      </Container>
    </section>
  );
}
