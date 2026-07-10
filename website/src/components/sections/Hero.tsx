import { getTranslations } from "next-intl/server";
import Container from "@/components/ui/Container";
import LinkButton from "@/components/corporate/ui/LinkButton";

export default async function Hero() {
  const t = await getTranslations("corporate.home.hero");

  return (
    <section className="relative min-h-[100svh] flex items-center overflow-hidden bg-white">
      <div className="absolute inset-0 grid-pattern opacity-50 pointer-events-none" aria-hidden />
      <div
        className="absolute inset-0 pointer-events-none"
        aria-hidden
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 50% -10%, rgba(37,99,235,0.08) 0%, transparent 55%)",
        }}
      />

      <Container className="relative z-10 pt-[calc(var(--nav-height)+2.5rem)] pb-16 sm:pt-[calc(var(--nav-height)+3rem)] sm:pb-20 lg:pb-24">
        <div className="max-w-3xl xl:max-w-4xl">
          <p className="pc-eyebrow hero-fade-up">{t("badge")}</p>

          <h1 className="pc-display mt-4 text-primary text-balance">{t("title")}</h1>

          <p className="mt-5 sm:mt-6 text-base sm:text-lg lg:text-xl text-muted leading-relaxed max-w-2xl hero-fade-up hero-fade-up-delay-1">
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
            <LinkButton href="/business#fleet" variant="outline" size="lg" trackSource="home-hero">
              {t("secondaryCta")}
            </LinkButton>
          </div>
        </div>
      </Container>
    </section>
  );
}
