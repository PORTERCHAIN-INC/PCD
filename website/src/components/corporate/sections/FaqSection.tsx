import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import Accordion from "@/components/ui/Accordion";
import { cn } from "@/lib/utils";

export interface FaqItem {
  question: string;
  answer: string;
}

interface FaqSectionProps {
  label?: string;
  title: string;
  items: FaqItem[];
  className?: string;
}

export default function FaqSection({ label, title, items, className }: FaqSectionProps) {
  return (
    <section className={cn("site-section bg-white", className)}>
      <Container size="narrow">
        <SectionHeader label={label} title={title} />
        <Accordion items={items} />
      </Container>
    </section>
  );
}
