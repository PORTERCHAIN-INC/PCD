import Container from "@/components/ui/Container";
import FadeIn from "@/components/corporate/motion/FadeIn";

interface StatItem {
  value: string;
  label: string;
}

interface StatsSectionProps {
  items: StatItem[];
  label?: string;
}

export default function StatsSection({ items, label }: StatsSectionProps) {
  return (
    <section className="py-14 md:py-16 bg-white border-y border-primary/[0.04]">
      <Container>
        {label && (
          <p className="text-center text-xs font-semibold uppercase tracking-wider text-muted mb-8">
            {label}
          </p>
        )}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 md:gap-6">
          {items.map((item, i) => (
            <FadeIn key={i} delay={i * 0.06} className="text-center">
              <p className="text-3xl sm:text-4xl font-semibold text-primary tracking-tight">
                {item.value}
              </p>
              <p className="mt-2 text-sm text-muted">{item.label}</p>
            </FadeIn>
          ))}
        </div>
      </Container>
    </section>
  );
}
