import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import FadeIn from "@/components/corporate/motion/FadeIn";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface BenefitItem {
  title: string;
  description: string;
  icon: LucideIcon;
}

interface BenefitsSectionProps {
  label: string;
  title: string;
  subtitle?: string;
  items: BenefitItem[];
}

export default function BenefitsSection({ label, title, subtitle, items }: BenefitsSectionProps) {
  return (
    <section className="site-section bg-white">
      <Container>
        <SectionHeader label={label} title={title} subtitle={subtitle} />
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {items.map((item, i) => (
            <FadeIn key={item.title} delay={i * 0.06}>
              <div
                className={cn(
                  "group card-surface card-surface-hover p-7 h-full",
                  i === 0 && "lg:col-span-1 border-t-2 border-t-secondary"
                )}
              >
                <div className="w-11 h-11 rounded-xl bg-secondary/10 flex items-center justify-center mb-5 group-hover:bg-secondary/15 transition-colors">
                  <item.icon className="w-5 h-5 text-secondary" aria-hidden />
                </div>
                <h3 className="text-lg font-semibold text-primary tracking-tight">{item.title}</h3>
                <p className="mt-2 text-sm text-muted leading-relaxed">{item.description}</p>
              </div>
            </FadeIn>
          ))}
        </div>
      </Container>
    </section>
  );
}
