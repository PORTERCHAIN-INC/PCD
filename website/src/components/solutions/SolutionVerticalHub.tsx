import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import FaqSection from "@/components/corporate/sections/FaqSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import LinkButton from "@/components/corporate/ui/LinkButton";
import InternalLinksBlock from "@/components/seo/InternalLinksBlock";
import {
  SOLUTION_HUB_CITY_SLUGS,
  SOLUTION_HUB_PROGRAMS,
  SOLUTION_MESSAGE_KEYS,
} from "@/lib/solutions-hub-config";
import type { SolutionVerticalSlug } from "@/lib/solutions-verticals";

interface SolutionVerticalHubProps {
  vertical: SolutionVerticalSlug;
}

export default async function SolutionVerticalHub({ vertical }: SolutionVerticalHubProps) {
  const messageKey = SOLUTION_MESSAGE_KEYS[vertical];
  const t = await getTranslations(`corporate.solutions.${messageKey}`);
  const source = `solutions/${vertical}`;
  const programs = SOLUTION_HUB_PROGRAMS[vertical];
  const citySlugs = SOLUTION_HUB_CITY_SLUGS[vertical];

  const programCards = programs.map(({ key, industrySlug, icon: Icon }) => (
    <article
      key={key}
      className="card-surface card-surface-hover group flex h-full flex-col p-7 sm:p-8"
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-secondary/10 text-secondary transition-colors group-hover:bg-secondary/15">
        <Icon className="h-6 w-6" aria-hidden />
      </div>
      <h3 className="mt-5 text-xl font-semibold text-primary tracking-tight">
        {t(`programs.items.${key}.title`)}
      </h3>
      <p className="mt-3 flex-1 text-sm text-muted leading-relaxed">
        {t(`programs.items.${key}.description`)}
      </p>
      <ul className="mt-4 space-y-2 text-sm text-primary/80">
        {[0, 1, 2].map((i) => (
          <li key={i} className="flex gap-2">
            <span className="text-secondary shrink-0" aria-hidden>
              •
            </span>
            <span>{t(`programs.items.${key}.bullets.${i}`)}</span>
          </li>
        ))}
      </ul>
      <div className="mt-6 flex flex-col sm:flex-row gap-3">
        <LinkButton href={`/industry/${industrySlug}`} showArrow trackSource={`${source}-${key}`}>
          {t(`programs.items.${key}.cta`)}
        </LinkButton>
        <LinkButton
          href={`/contact?intent=quote&from=${source}-${key}`}
          variant="outline"
          size="sm"
          trackSource={`${source}-${key}-quote`}
        >
          {t("programs.quoteCta")}
        </LinkButton>
      </div>
    </article>
  ));

  const personaItems = [0, 1, 2, 3].map((i) => ({
    title: t(`personas.items.${i}.title`),
    description: t(`personas.items.${i}.description`),
  }));

  const cityLinks = citySlugs.map((slug) => ({
    href: `/service-areas/${slug}`,
    label: t(`cities.items.${slug}`),
  }));

  const faqItems = [0, 1, 2, 3].map((i) => ({
    question: t(`faq.items.${i}.q`),
    answer: t(`faq.items.${i}.a`),
  }));

  return (
    <>
      <section className="site-section bg-white">
        <Container>
          <SectionHeader
            label={t("programs.label")}
            title={t("programs.title")}
            subtitle={t("programs.subtitle")}
          />
          <div className="grid gap-5 lg:grid-cols-3">{programCards}</div>
          <p className="mt-8 text-center text-sm text-muted">
            {t("programs.alsoBrowse")}{" "}
            <Link href="/industry" className="font-semibold text-secondary hover:underline">
              {t("programs.allIndustries")}
            </Link>
            {" · "}
            <Link href="/solutions" className="font-semibold text-secondary hover:underline">
              {t("programs.allSolutions")}
            </Link>
            {" · "}
            <Link href="/service-areas" className="font-semibold text-secondary hover:underline">
              {t("programs.allServiceAreas")}
            </Link>
          </p>
        </Container>
      </section>

      <FeatureSection
        label={t("personas.label")}
        title={t("personas.title")}
        subtitle={t("personas.subtitle")}
        items={personaItems}
        variant="grid"
        className="bg-gray-bg"
      />

      {cityLinks.length > 0 && <InternalLinksBlock title={t("cities.title")} links={cityLinks} />}

      <section className="site-section bg-gray-bg border-t border-primary/6">
        <Container className="max-w-3xl text-center">
          <p className="text-muted leading-relaxed">{t("bridge.body")}</p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <LinkButton href="/platform" variant="outline" trackSource={source}>
              {t("bridge.platform")}
            </LinkButton>
            <LinkButton href="/trust" variant="outline" trackSource={source}>
              {t("bridge.trust")}
            </LinkButton>
            <LinkButton href="/business" variant="outline" trackSource={source}>
              {t("bridge.business")}
            </LinkButton>
          </div>
        </Container>
      </section>

      <FaqSection label={t("faq.label")} title={t("faq.title")} items={faqItems} />

      <CtaSection
        title={t("cta.title")}
        subtitle={t("cta.subtitle")}
        primaryLabel={t("cta.primary")}
        primaryHref={`/contact?intent=quote&from=${source}`}
        secondaryLabel={t("cta.secondary")}
        secondaryHref="/business#fleet"
        variant="gradient"
        trackSource={source}
      />
    </>
  );
}
