import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import VehiclesTabNav from "@/components/vehicles/VehiclesTabNav";
import HeroSection from "@/components/corporate/sections/HeroSection";
import HeroPhoto from "@/components/ui/HeroPhoto";
import CtaSection from "@/components/corporate/sections/CtaSection";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import FadeIn from "@/components/corporate/motion/FadeIn";
import LinkButton from "@/components/corporate/ui/LinkButton";
import { siteImages } from "@/data/site-images";
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
      <HeroSection
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("hero.primaryCta")}
        primaryHref="/contact?intent=quote&from=vehicles"
        secondaryCta={t("hero.secondaryCta")}
        secondaryHref="/business"
        variant="light-centered"
        illustration={<HeroPhoto image={siteImages.hero.gta} />}
        trackSource="vehicles"
      />
      <section className="site-section bg-white">
        <Container>
          <SectionHeader label={t("cards.label")} title={t("cards.title")} />
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {cards.map((card, i) => (
              <FadeIn key={card.id} delay={i * 0.06}>
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
              </FadeIn>
            ))}
          </div>
        </Container>
      </section>
      <CtaSection
        title={t("cta.title")}
        subtitle={t("cta.subtitle")}
        primaryLabel={t("cta.primary")}
        primaryHref="/contact?intent=quote&from=vehicles"
        secondaryLabel={t("cta.secondary")}
        secondaryHref="/solutions"
        variant="gradient"
        trackSource="vehicles"
      />
    </CorporateShell>
  );
}
