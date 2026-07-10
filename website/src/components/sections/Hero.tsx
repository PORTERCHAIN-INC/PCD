import { getTranslations } from "next-intl/server";
import Container from "@/components/ui/Container";
import LinkButton from "@/components/corporate/ui/LinkButton";
import SiteImage from "@/components/ui/SiteImage";
import { siteImages } from "@/data/site-images";

export default async function Hero() {
  const t = await getTranslations("corporate.home.hero");

  return (
    <section className="relative min-h-[100svh] overflow-hidden bg-white">
      <div className="grid min-h-[100svh] lg:grid-cols-[minmax(0,1fr)_minmax(0,1.08fr)]">
        {/* Copy — left on desktop, below image on mobile */}
        <div className="relative z-20 order-2 flex items-center lg:order-1">
          <div
            className="absolute inset-0 grid-pattern opacity-40 pointer-events-none"
            aria-hidden
          />
          <div
            className="absolute inset-0 pointer-events-none hero-merge-panel hidden lg:block"
            aria-hidden
          />
          <div
            className="absolute inset-y-0 -right-6 z-10 hidden w-28 lg:block hero-merge-blur pointer-events-none"
            aria-hidden
          />
          <div
            className="absolute inset-0 pointer-events-none lg:hidden"
            aria-hidden
            style={{
              background:
                "linear-gradient(to bottom, transparent 0%, rgba(255,255,255,0.85) 28%, white 45%)",
            }}
          />

          <Container className="relative z-10 w-full pt-6 pb-14 sm:pb-16 lg:pt-[calc(var(--nav-height)+2.5rem)] lg:pb-20 xl:pb-24 lg:pr-4 xl:pr-8">
            <div className="max-w-xl xl:max-w-2xl">
              <p className="pc-eyebrow hero-fade-up">{t("badge")}</p>

              <h1 className="pc-display mt-4 text-primary text-balance hero-fade-up hero-fade-up-delay-1">
                {t("title")}
              </h1>

              <p className="mt-5 sm:mt-6 text-base sm:text-lg lg:text-xl text-muted leading-relaxed max-w-xl hero-fade-up hero-fade-up-delay-1">
                {t("subtitle")}
              </p>

              <div className="mt-8 sm:mt-10 flex flex-col sm:flex-row flex-wrap gap-3 hero-fade-up hero-fade-up-delay-2">
                <LinkButton
                  href="/contact?intent=quote&from=home-hero"
                  size="lg"
                  trackSource="home-hero"
                >
                  {t("primaryCta")}
                </LinkButton>
                <LinkButton
                  href="/business#fleet"
                  variant="outline"
                  size="lg"
                  trackSource="home-hero"
                >
                  {t("secondaryCta")}
                </LinkButton>
              </div>
            </div>
          </Container>
        </div>

        {/* Branded truck — right on desktop, top on mobile */}
        <div className="relative order-1 min-h-[44svh] sm:min-h-[48svh] lg:order-2 lg:min-h-0">
          <SiteImage
            image={siteImages.hero.welcome}
            fill
            priority
            className="object-cover object-[62%_center]"
            sizes="(max-width: 1024px) 100vw, 54vw"
          />

          {/* Mobile: fade into copy below */}
          <div
            className="absolute inset-0 pointer-events-none lg:hidden"
            aria-hidden
            style={{
              background:
                "linear-gradient(to bottom, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.55) 62%, white 100%)",
            }}
          />

          {/* Desktop: blur-merge seam into left panel */}
          <div
            className="absolute inset-y-0 left-0 hidden w-[46%] hero-image-fade-left pointer-events-none lg:block"
            aria-hidden
          />
          <div
            className="absolute inset-y-0 left-0 hidden w-[22%] hero-merge-blur pointer-events-none lg:block"
            aria-hidden
          />

          {/* Subtle brand glow on warehouse floor */}
          <div
            className="absolute bottom-0 right-0 h-2/5 w-3/5 pointer-events-none"
            aria-hidden
            style={{
              background:
                "radial-gradient(ellipse 80% 70% at 85% 100%, rgba(34,197,94,0.12) 0%, transparent 70%)",
            }}
          />
        </div>
      </div>
    </section>
  );
}
