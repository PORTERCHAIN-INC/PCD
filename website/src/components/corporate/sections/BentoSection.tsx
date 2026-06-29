import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import FadeIn from "@/components/corporate/motion/FadeIn";
import { cn } from "@/lib/utils";

interface BentoItem {
  title: string;
  description: string;
  className?: string;
}

interface BentoSectionProps {
  label?: string;
  title: string;
  subtitle?: string;
  items: BentoItem[];
  className?: string;
}

export default function BentoSection({
  label,
  title,
  subtitle,
  items,
  className,
}: BentoSectionProps) {
  return (
    <section className={cn("site-section bg-white", className)}>
      <Container>
        <SectionHeader label={label} title={title} subtitle={subtitle} />
        <div className="grid md:grid-cols-3 gap-4 auto-rows-fr">
          {items.map((item, i) => (
            <FadeIn
              key={i}
              delay={i * 0.05}
              className={cn(
                "card-surface card-surface-hover p-7",
                item.className,
                i === 0 && "md:col-span-2 md:row-span-1 bg-primary text-white border-primary",
                i === 3 && "md:col-span-2"
              )}
            >
              <h3
                className={cn(
                  "text-lg font-semibold tracking-tight",
                  i === 0 ? "text-white" : "text-primary"
                )}
              >
                {item.title}
              </h3>
              <p
                className={cn(
                  "mt-2 text-sm leading-relaxed",
                  i === 0 ? "text-white/65" : "text-muted"
                )}
              >
                {item.description}
              </p>
            </FadeIn>
          ))}
        </div>
      </Container>
    </section>
  );
}
