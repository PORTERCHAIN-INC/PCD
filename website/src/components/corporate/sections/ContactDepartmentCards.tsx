import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import FadeIn from "@/components/corporate/motion/FadeIn";
import type { LucideIcon } from "lucide-react";

export interface DepartmentCard {
  title: string;
  description: string;
  contact: string;
  href: string;
  icon: LucideIcon;
}

interface ContactDepartmentCardsProps {
  label: string;
  title: string;
  items: DepartmentCard[];
}

export default function ContactDepartmentCards({
  label,
  title,
  items,
}: ContactDepartmentCardsProps) {
  return (
    <section className="site-section bg-gray-bg border-t border-primary/[0.04]">
      <Container>
        <SectionHeader label={label} title={title} align="left" className="max-w-xl mb-10" />
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((item, i) => (
            <FadeIn key={item.title} delay={i * 0.06}>
              <a
                href={item.href}
                className="group card-surface card-surface-hover p-6 flex flex-col h-full"
              >
                <div className="w-10 h-10 rounded-xl bg-secondary/10 flex items-center justify-center mb-4 group-hover:bg-secondary/15 transition-colors">
                  <item.icon className="w-5 h-5 text-secondary" aria-hidden />
                </div>
                <h3 className="text-base font-semibold text-primary group-hover:text-secondary transition-colors">
                  {item.title}
                </h3>
                <p className="mt-2 text-sm text-muted leading-relaxed flex-1">{item.description}</p>
                <p className="mt-4 text-sm font-medium text-secondary">{item.contact}</p>
              </a>
            </FadeIn>
          ))}
        </div>
      </Container>
    </section>
  );
}
