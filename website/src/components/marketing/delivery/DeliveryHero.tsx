import Container from "@/components/ui/Container";
import PageBreadcrumbs, { type BreadcrumbItem } from "@/components/seo/PageBreadcrumbs";
import NetworkGraphic from "@/components/marketing/home/HomeHeroImage";
import TrustBadges from "@/components/marketing/ui/TrustBadges";
import type { VerticalPhoto } from "@/components/marketing/delivery/vertical-visuals";

/**
 * Dark hero shared by the calculator and /delivery pages — same visual language as the home hero
 * (navy, blue glow, the SVG network graphic on desktop only — no photography, so LCP is the heading text).
 */
export default function DeliveryHero({
  locale,
  crumbs,
  eyebrow,
  title,
  answer,
  actions,
  facts,
  image,
  children,
}: {
  locale: string;
  crumbs: BreadcrumbItem[];
  eyebrow?: string;
  /** The H1 (plain string or a HeroVariantTitle element). */
  title: React.ReactNode;
  answer: string;
  actions?: React.ReactNode;
  facts?: Array<{ label: string; value: string }>;
  image?: VerticalPhoto;
  children?: React.ReactNode;
}) {
  return (
    <section className="relative isolate overflow-hidden bg-primary text-white">
      <div
        className="pointer-events-none absolute -left-40 -top-40 -z-10 h-[30rem] w-[30rem] rounded-full bg-secondary/25 blur-3xl"
        aria-hidden
      />
      <Container className="pb-12 pt-[calc(var(--nav-height)+1rem)] sm:pb-16">
        <PageBreadcrumbs tone="dark" items={crumbs} />
        <div
          className={
            image
              ? "mt-8 grid gap-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:items-center lg:gap-14"
              : "mt-8"
          }
        >
          <div className="max-w-3xl">
            {eyebrow ? (
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#93c5fd] sm:text-sm">
                {eyebrow}
              </p>
            ) : null}
            <div className="mt-3">{title}</div>
            <p className="mt-5 max-w-2xl border-l-2 border-[#93c5fd]/60 pl-4 text-base leading-relaxed text-white/85 sm:text-lg">
              {answer}
            </p>
            {actions ? <div className="mt-7">{actions}</div> : null}
            <TrustBadges locale={locale} tone="dark" className="mt-7" />
          </div>
          {image ? (
            <div
              className="relative hidden aspect-[16/10] overflow-hidden rounded-3xl bg-white/[0.03] ring-1 ring-white/10 lg:block"
              aria-hidden
            >
              <NetworkGraphic />
            </div>
          ) : null}
        </div>
        {facts?.length ? (
          <dl className="mt-10 grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
            {facts.map((f) => (
              <div
                key={f.label}
                className="rounded-2xl border border-white/10 bg-white/[0.06] px-4 py-3.5"
              >
                <dt className="text-xs font-medium uppercase tracking-wide text-white/65">
                  {f.label}
                </dt>
                <dd className="mt-1 text-base font-semibold text-white">{f.value}</dd>
              </div>
            ))}
          </dl>
        ) : null}
        {children}
      </Container>
    </section>
  );
}
