import Image from "next/image";
import { getTranslations } from "next-intl/server";
import Container from "@/components/ui/Container";
import PorterchainWordmark from "@/components/marketing/brand/PorterchainWordmark";
import ReviewsProof from "@/components/marketing/ReviewsProof";
import { MERCHANT_LOGOS } from "@/data/merchant-logos";
import { CALCULATOR_VEHICLES } from "@/lib/marketing/calculator-lead";
import { DELIVERY_AREAS, ENTITY_FACTS } from "@/lib/seo/delivery-programmatic";
import { GTA150_FSA_CODES } from "@/lib/seo/gta150FsaCodes";

/**
 * Credibility strip — real data only:
 *  - coverage numbers are computed from the generated FSA list (334, same as the pricing engine),
 *    the published delivery areas and the instant-price vehicle classes;
 *  - our own brand (PorterChain mark + legal entity) instead of customer logos; customer logos
 *    render only when `MERCHANT_LOGOS` has permissioned entries (none today);
 *  - reviews render only when verified reviews / a Google rating are configured (ReviewsProof).
 * No invented counts, ratings or quotes.
 */
export default async function HomeTrustStrip({ locale }: { locale: string }) {
  const t = await getTranslations({ locale, namespace: "homePage" });
  const facts = [
    {
      value: t("coverage.postalAreas", { count: GTA150_FSA_CODES.size }),
      hint: t("coverage.postalAreasHint"),
    },
    { value: t("coverage.areas", { count: DELIVERY_AREAS.length }), hint: t("coverage.areasHint") },
    {
      value: t("coverage.vehicles", { count: CALCULATOR_VEHICLES.length }),
      hint: t("coverage.vehiclesHint"),
    },
  ];

  return (
    <>
      <section aria-label={t("coverage.ariaLabel")} className="border-b border-primary/8 bg-white">
        <Container className="grid gap-8 py-10 sm:py-12 lg:grid-cols-[minmax(0,15rem)_1fr] lg:items-center lg:gap-12">
          <div className="flex items-center gap-4 lg:block">
            <PorterchainWordmark tone="light" size="lg" />
            <p className="text-sm leading-relaxed text-muted lg:mt-3">
              {t("brand.operatedBy", { legalName: ENTITY_FACTS.legalName })}
            </p>
          </div>
          <dl className="grid gap-6 sm:grid-cols-3 sm:gap-8">
            {facts.map((fact) => (
              <div key={fact.value} className="border-l-2 border-secondary pl-4">
                <dt className="text-2xl font-semibold tracking-tight text-primary">{fact.value}</dt>
                <dd className="mt-1 text-sm leading-relaxed text-muted">{fact.hint}</dd>
              </div>
            ))}
          </dl>
          {MERCHANT_LOGOS.length > 0 ? (
            <div className="border-t border-primary/8 pt-6 lg:col-span-2">
              <p className="text-center text-xs font-semibold uppercase tracking-[0.14em] text-muted">
                {t("trust.logosTitle")}
              </p>
              <ul className="mt-4 flex flex-wrap items-center justify-center gap-x-10 gap-y-4">
                {MERCHANT_LOGOS.map((logo) => (
                  <li key={logo.name}>
                    <Image
                      src={logo.src}
                      alt={logo.name}
                      width={logo.width}
                      height={logo.height}
                      className="h-8 w-auto opacity-80 grayscale"
                    />
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </Container>
      </section>
      <ReviewsProof locale={locale} />
    </>
  );
}
