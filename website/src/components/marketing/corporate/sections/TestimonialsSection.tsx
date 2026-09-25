import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import FadeIn from "@/components/marketing/corporate/motion/FadeIn";

interface Testimonial {
  quote: string;
  name: string;
  role: string;
}

interface TestimonialsSectionProps {
  label: string;
  title: string;
  items: Testimonial[];
}

export default function TestimonialsSection({ label, title, items }: TestimonialsSectionProps) {
  return (
    <section className="site-section bg-white overflow-hidden">
      <Container>
        <SectionHeader label={label} title={title} />
        <div className="grid md:grid-cols-3 gap-5">
          {items.map((item, i) => (
            <FadeIn key={i} delay={i * 0.1}>
              <blockquote className="card-surface p-7 h-full flex flex-col">
                <div className="text-secondary text-4xl font-serif leading-none mb-4" aria-hidden>
                  &ldquo;
                </div>
                <p className="text-sm text-primary/85 leading-relaxed flex-1">{item.quote}</p>
                <footer className="mt-6 pt-5 border-t border-primary/[0.06]">
                  <cite className="not-italic">
                    <p className="text-sm font-semibold text-primary">{item.name}</p>
                    <p className="text-xs text-muted mt-0.5">{item.role}</p>
                  </cite>
                </footer>
              </blockquote>
            </FadeIn>
          ))}
        </div>
      </Container>
    </section>
  );
}
