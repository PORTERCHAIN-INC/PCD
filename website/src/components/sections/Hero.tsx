import { getTranslations } from "next-intl/server";
import Container from "@/components/ui/Container";
import SiteImage from "@/components/ui/SiteImage";
import HeroCopy from "@/components/sections/HeroCopy";
import { siteImages } from "@/data/site-images";

type HeroProps = {
  locale: string;
};

/**
 * Home hero — 45% copy / 55% fleet photo.
 * Fleet stays sharp (unoptimized); white edge overlays merge it into the page bg.
 */
export default async function Hero({ locale }: HeroProps) {
  const t = await getTranslations("corporate.home.hero");
  const fleet = siteImages.hero.welcome;

  return (
    <section className="relative overflow-x-clip bg-white">
      <div className="grid lg:min-h-[100svh] lg:grid-cols-[minmax(0,45%)_minmax(0,55%)] lg:items-center">
        {/* 45% — headline + CTA */}
        <div className="relative z-20 order-2 flex items-center lg:order-1">
          <div
            className="absolute inset-0 grid-pattern opacity-40 pointer-events-none"
            aria-hidden
          />
          <div
            className="hero-merge-panel absolute inset-0 pointer-events-none hidden lg:block"
            aria-hidden
          />

          <Container className="relative z-10 w-full !max-w-none px-5 py-10 sm:px-8 sm:py-12 lg:pl-8 lg:pr-2 lg:pt-[calc(var(--nav-height)+1.5rem)] lg:pb-16 xl:pl-12 xl:pr-4">
            <HeroCopy
              locale={locale}
              badge={t("badge")}
              title={t("title")}
              titleHighlight={t("titleHighlight")}
              subtitle={t("subtitle")}
              primaryCta={t("primaryCta")}
              secondaryCta={t("secondaryCta")}
              trustLine={t("trustLine")}
              trustProof={t("trustProof")}
              trustAreas={t("trustAreas")}
              slaLabel={t("slaLabel")}
              slaExpired={t("slaExpired")}
            />
          </Container>
        </div>

        {/* 55% — full fleet, sharp, merged into white */}
        <div className="relative order-1 bg-white lg:order-2 lg:pt-[var(--nav-height)]">
          <div className="hero-fleet-stage relative mx-auto w-full overflow-visible lg:my-2 lg:mr-0">
            <div className="hero-fleet-scale relative w-full">
              <SiteImage
                image={fleet}
                priority
                unoptimized
                className="hero-fleet-photo block h-auto w-full max-w-none"
                sizes="(max-width: 1024px) 100vw, 55vw"
              />

              {/* Soft dissolve into page background (no CSS blur on pixels) */}
              <div className="hero-fleet-merge pointer-events-none absolute inset-0" aria-hidden />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
