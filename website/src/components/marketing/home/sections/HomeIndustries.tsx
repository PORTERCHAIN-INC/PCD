import { getTranslations } from "next-intl/server";
import { ArrowRight, Building2, HardHat, Pill, ShoppingBag, Sofa } from "lucide-react";
import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/marketing/ui/SectionHeader";

/** Industry tiles → /delivery/{vertical} hubs (furniture has its own hub since Oct 2026). */
const TILES = [
  { id: "shopify", href: "/delivery/shopify-merchants", Icon: ShoppingBag },
  { id: "pharmacy", href: "/delivery/pharmacy", Icon: Pill },
  { id: "furniture", href: "/delivery/furniture", Icon: Sofa },
  { id: "construction", href: "/delivery/construction", Icon: HardHat },
  { id: "warehouses", href: "/delivery/warehouses", Icon: Building2 },
] as const;

export default async function HomeIndustries({ locale }: { locale: string }) {
  const t = await getTranslations({ locale, namespace: "homePage.industries" });
  return (
    <section className="bg-gray-bg" aria-labelledby="home-industries-heading">
      <Container className="py-16 sm:py-24">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <SectionHeader id="home-industries-heading" eyebrow={t("eyebrow")} title={t("title")} />
          <Link
            href="/delivery"
            className="inline-flex min-h-[var(--touch-min)] items-center gap-1.5 rounded text-sm font-semibold text-secondary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary"
          >
            {t("all")}
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
        </div>
        <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {TILES.map(({ id, href, Icon }) => (
            <li key={id}>
              <Link
                href={href}
                className="group flex h-full flex-col rounded-2xl border border-primary/8 bg-white p-6 transition-[border-color,box-shadow,transform] duration-200 hover:border-secondary/40 hover:shadow-xl hover:shadow-primary/8 motion-safe:hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary focus-visible:ring-offset-2"
              >
                <span
                  className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-white`}
                >
                  <Icon className="h-6 w-6" aria-hidden />
                </span>
                <span className="mt-5 flex items-center gap-1.5 text-lg font-semibold text-primary">
                  {t(`items.${id}.title`)}
                  <ArrowRight
                    className="h-4 w-4 text-secondary transition-transform motion-safe:group-hover:translate-x-1"
                    aria-hidden
                  />
                </span>
                <span className="mt-1.5 block text-sm leading-relaxed text-muted">
                  {t(`items.${id}.body`)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </Container>
    </section>
  );
}
