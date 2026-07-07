import { cn } from "@/lib/utils";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import FadeIn from "@/components/corporate/motion/FadeIn";
import { Link } from "@/i18n/navigation";
import { ArrowUpRight } from "lucide-react";

export interface CardItem {
  title: string;
  description: string;
  id?: string;
  detail?: string;
}

interface CardGridSectionProps {
  label?: string;
  title: string;
  subtitle?: string;
  items: CardItem[];
  variant?: "default" | "mosaic" | "contact";
  className?: string;
}

export default function CardGridSection({
  label,
  title,
  subtitle,
  items,
  variant = "default",
  className,
}: CardGridSectionProps) {
  if (variant === "mosaic") {
    return (
      <section className={cn("site-section bg-gray-bg", className)}>
        <Container>
          <SectionHeader label={label} title={title} subtitle={subtitle} />
          <div className="grid md:grid-cols-2 gap-5">
            {items.map((item, i) => (
              <FadeIn key={i} delay={i * 0.08}>
                <article
                  id={item.id}
                  className={cn(
                    "card-surface card-surface-hover p-8 h-full",
                    i === 0 && "md:row-span-1 bg-primary text-white border-primary"
                  )}
                >
                  <h3
                    className={cn(
                      "text-xl font-semibold tracking-tight",
                      i === 0 ? "text-white" : "text-primary"
                    )}
                  >
                    {item.title}
                  </h3>
                  <p
                    className={cn(
                      "mt-3 leading-relaxed",
                      i === 0 ? "text-white/65" : "text-muted text-sm"
                    )}
                  >
                    {item.description}
                  </p>
                </article>
              </FadeIn>
            ))}
          </div>
        </Container>
      </section>
    );
  }

  if (variant === "contact") {
    return (
      <section className={cn("site-section bg-white", className)}>
        <Container>
          <SectionHeader label={label} title={title} align="left" className="max-w-xl" />
          <div className="grid sm:grid-cols-3 gap-5 mt-10">
            {items.map((item, i) => (
              <FadeIn key={i} delay={i * 0.08}>
                <div className="card-surface p-6 h-full">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-secondary mb-2">
                    {item.title}
                  </h3>
                  <p className="text-base font-semibold text-primary">{item.description}</p>
                  {item.detail && <p className="mt-1 text-sm text-muted">{item.detail}</p>}
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
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {items.map((item, i) => (
            <FadeIn key={i} delay={i * 0.06}>
              <article id={item.id} className="card-surface card-surface-hover p-6 h-full">
                <h3 className="text-base font-semibold text-primary tracking-tight">
                  {item.title}
                </h3>
                <p className="mt-2 text-sm text-muted leading-relaxed">{item.description}</p>
              </article>
            </FadeIn>
          ))}
        </div>
      </Container>
    </section>
  );
}

export interface ResourceItem {
  title: string;
  description: string;
  href: string;
}

export function RelatedResourcesSection({
  label,
  title,
  items,
  className,
}: {
  label?: string;
  title: string;
  items: ResourceItem[];
  className?: string;
}) {
  return (
    <section className={cn("site-section bg-gray-bg border-t border-primary/[0.04]", className)}>
      <Container>
        <SectionHeader label={label} title={title} align="left" className="mb-8" />
        <div className="grid sm:grid-cols-3 gap-4">
          {items.map((item, i) => (
            <FadeIn key={i} delay={i * 0.06}>
              <Link
                href={item.href}
                className="group card-surface card-surface-hover p-6 flex flex-col h-full"
              >
                <h3 className="text-base font-semibold text-primary group-hover:text-secondary transition-colors">
                  {item.title}
                </h3>
                <p className="mt-2 text-sm text-muted leading-relaxed flex-1">{item.description}</p>
                <ArrowUpRight className="w-4 h-4 text-secondary mt-4 opacity-0 group-hover:opacity-100 transition-opacity" />
              </Link>
            </FadeIn>
          ))}
        </div>
      </Container>
    </section>
  );
}
