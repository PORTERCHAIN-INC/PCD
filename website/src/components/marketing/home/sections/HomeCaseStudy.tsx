import { Quote } from "lucide-react";
import Container from "@/components/ui/Container";
import { PUBLISHED_CASE_STUDIES } from "@/data/case-studies";

/** Case-study slot — renders nothing until a study is published with the customer's permission. */
export default function HomeCaseStudy() {
  const study = PUBLISHED_CASE_STUDIES[0];
  if (!study) return null;
  return (
    <section className="bg-white" aria-labelledby="home-case-heading" data-testid="case-study">
      <Container className="py-16 sm:py-24">
        <div className="grid gap-10 rounded-3xl border border-primary/8 bg-gray-bg p-8 sm:p-12 lg:grid-cols-[1.4fr_1fr]">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.14em] text-secondary">
              {study.customer}
            </p>
            <h2
              id="home-case-heading"
              className="mt-2 text-balance text-3xl font-semibold tracking-tight text-primary"
            >
              {study.headline}
            </h2>
            {study.quote ? (
              <blockquote className="mt-6 text-lg leading-relaxed text-primary/90">
                <Quote className="mb-2 h-6 w-6 text-secondary" aria-hidden />
                <p>{study.quote.text}</p>
                <footer className="mt-3 text-sm text-muted">
                  {study.quote.author}, {study.quote.role}
                </footer>
              </blockquote>
            ) : null}
          </div>
          {study.facts.length ? (
            <dl className="grid content-center gap-6">
              {study.facts.map((f) => (
                <div key={f.label}>
                  <dt className="text-sm text-muted">{f.label}</dt>
                  <dd className="text-2xl font-semibold text-primary">{f.value}</dd>
                </div>
              ))}
            </dl>
          ) : null}
        </div>
      </Container>
    </section>
  );
}
