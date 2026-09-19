"use client";

import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import Accordion from "@/components/ui/Accordion";
import BlurFade from "@/components/magic/blur-fade";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

export type PersonaItem = {
  title: string;
  description: string;
  trustHref?: string;
  trustLabel?: string;
};

export type PersonaAudienceContent = {
  label?: string;
  title: string;
  subtitle?: string;
  items: PersonaItem[];
};

interface PersonaAudienceSectionProps {
  content: PersonaAudienceContent;
  className?: string;
}

export default function PersonaAudienceSection({
  content,
  className,
}: PersonaAudienceSectionProps) {
  return (
    <section className={cn("site-section bg-gray-bg grid-pattern", className)}>
      <Container size="narrow">
        <BlurFade inView>
          <SectionHeader label={content.label} title={content.title} subtitle={content.subtitle} />
        </BlurFade>
        <BlurFade delay={0.06} inView>
          <Accordion
            items={content.items.map((item) => ({
              question: item.title,
              answer: item.trustHref ? (
                <>
                  {item.description}{" "}
                  <Link
                    href={item.trustHref}
                    className="font-semibold text-secondary hover:underline"
                  >
                    {item.trustLabel ?? "Trust & documentation"}
                  </Link>
                </>
              ) : (
                item.description
              ),
            }))}
          />
        </BlurFade>
      </Container>
    </section>
  );
}
