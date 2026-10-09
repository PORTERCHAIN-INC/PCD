import { Link } from "@/i18n/navigation";
import { DELIVERY_VEHICLES } from "@/lib/seo/delivery-programmatic";
import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import VehiclesTabNav from "@/components/marketing/vehicles/VehiclesTabNav";
import MarketingHero from "@/components/marketing/MarketingHero";
import MarketingCloser from "@/components/marketing/MarketingCloser";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import LinkButton from "@/components/marketing/corporate/ui/LinkButton";
import { VEHICLES_TAB_ITEMS } from "@/data/vehicles-navigation";

type Props = { params: Promise<{ locale: string }> };

const HUB_CARD_IDS = ["cargoVan", "tradeVan", "boxTruck", "pickupTruck"] as const;

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.vehicles" });
  return buildPageMetadata(locale, "vehicles", t("title"), t("description"));
}

export default async function VehiclesHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("corporate.vehiclesIndex");
  const tCta = await getTranslations("common.cta");
  const tBc = await getTranslations("corporate.breadcrumbs");
  const tMenu = await getTranslations("corporate.nav.vehiclesMenu");

  const cards = HUB_CARD_IDS.map((id) => {
    const href = VEHICLES_TAB_ITEMS.find((item) => item.id === id)?.href ?? "/vehicles";
    return {
      id,
      href,
      title: tMenu(`${id}.label`),
      description: tMenu(`${id}.description`),
    };
  });

  return (
    <CorporateShell>
      <PageBreadcrumbs items={[{ label: tBc("home"), href: "/" }, { label: tBc("vehicles") }]} />
      <VehiclesTabNav />
      <MarketingHero
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={tCta("quote")}
        primaryHref="/sign-up?intent=quote&from=vehicles"
        secondaryCta={t("hero.secondaryCta")}
        secondaryHref="/business"
        variant="light-centered"
        trackSource="vehicles"
      />
      <section className="bg-gray-bg" aria-labelledby="vehicles-book-heading">
        <Container className="py-14 sm:py-20">
          <h2
            id="vehicles-book-heading"
            className="text-2xl font-semibold tracking-tight text-primary sm:text-3xl"
          >
            {locale === "fr"
              ? "Réservable en ligne, prix instantané"
              : "Bookable online, priced instantly"}
          </h2>
          <p className="mt-2 max-w-2xl text-muted">
            {locale === "fr"
              ? "Trois classes, toutes conduites avec un permis G standard. Le prix dépend de la distance et du véhicule, TVH incluse."
              : "Three classes, all driven on a standard Ontario G licence. Price depends on distance and vehicle, HST included."}
          </p>
          <div
            className="mt-8 overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-labelledby="vehicles-book-heading"
          >
            <table className="w-full min-w-[36rem] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-primary/15 text-xs uppercase tracking-wide text-muted">
                  <th scope="col" className="py-3 pr-4 font-semibold">
                    {locale === "fr" ? "Véhicule" : "Vehicle"}
                  </th>
                  <th scope="col" className="py-3 pr-4 font-semibold">
                    {locale === "fr" ? "Capacité" : "Capacity"}
                  </th>
                  <th scope="col" className="py-3 font-semibold">
                    {locale === "fr" ? "Idéal pour" : "Best for"}
                  </th>
                </tr>
              </thead>
              <tbody>
                {Object.values(DELIVERY_VEHICLES).map((v) => (
                  <tr key={v.id} className="border-b border-primary/10 align-top">
                    <th scope="row" className="py-4 pr-4 font-semibold text-primary">
                      {v.label}
                    </th>
                    <td className="py-4 pr-4 text-primary">{v.capacity}</td>
                    <td className="py-4 text-muted">{v.bestFor}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Link
            href="/delivery-cost-calculator?from=vehicles"
            className="mt-6 inline-flex min-h-11 items-center gap-2 rounded-full bg-primary px-6 text-sm font-semibold text-white hover:bg-[#152238] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary focus-visible:ring-offset-2"
          >
            {locale === "fr" ? "Obtenir un prix" : "Get a price"}
          </Link>
        </Container>
      </section>
      <section className="site-section bg-white">
        <Container>
          <SectionHeader label={t("cards.label")} title={t("cards.title")} />
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {cards.map((card) => (
              <div key={card.id}>
                <article className="card-surface card-surface-hover p-5 h-full flex flex-col">
                  <h3 className="text-lg font-semibold text-primary">{card.title}</h3>
                  <p className="mt-2 text-sm text-muted leading-relaxed flex-1">
                    {card.description}
                  </p>
                  <div className="mt-4">
                    <LinkButton href={card.href} size="sm" showArrow trackSource="vehicles">
                      {t("cards.viewVehicle")}
                    </LinkButton>
                  </div>
                </article>
              </div>
            ))}
          </div>
        </Container>
      </section>
      <MarketingCloser
        title={t("cta.title")}
        subtitle={t("cta.subtitle")}
        primaryLabel={tCta("quote")}
        primaryHref="/sign-up?intent=quote&from=vehicles"
        secondaryLabel={t("cta.secondary")}
        secondaryHref="/delivery"
        variant="gradient"
        trackSource="vehicles"
      />
    </CorporateShell>
  );
}
