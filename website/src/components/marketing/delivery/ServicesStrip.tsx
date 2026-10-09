import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import Container from "@/components/ui/Container";
import { DELIVERY_VERTICALS, deliveryPagePath } from "@/lib/seo/delivery-programmatic";
import { VERTICAL_ICONS } from "@/components/marketing/delivery/vertical-visuals";

/** The one services row per page: the five industries, current one marked. */
export default function ServicesStrip({ current }: { current?: string }) {
  return (
    <section
      aria-labelledby="services-strip-heading"
      className="border-y border-primary/8 bg-white"
    >
      <Container className="py-6">
        <h2
          id="services-strip-heading"
          className="text-xs font-semibold uppercase tracking-wide text-muted"
        >
          Industries we serve
        </h2>
        <ul className="mt-3 flex flex-wrap gap-2" data-testid="services-strip">
          {DELIVERY_VERTICALS.map((v) => {
            const Icon = VERTICAL_ICONS[v.slug];
            const active = v.slug === current;
            return (
              <li key={v.slug}>
                <Link
                  href={`/${deliveryPagePath(v.slug)}`}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "inline-flex min-h-10 items-center gap-2 rounded-full border px-4 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary",
                    active
                      ? "border-primary bg-primary text-white"
                      : "border-primary/12 text-primary hover:border-secondary hover:text-secondary"
                  )}
                >
                  {Icon ? <Icon className="h-4 w-4" aria-hidden /> : null}
                  {v.name}
                </Link>
              </li>
            );
          })}
        </ul>
      </Container>
    </section>
  );
}
