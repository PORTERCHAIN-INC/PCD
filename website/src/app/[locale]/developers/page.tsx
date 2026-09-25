import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { BookOpen, Code2, FileJson, KeyRound, Webhook } from "lucide-react";
import { routing } from "@/i18n/routing";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import MarketingHero from "@/components/marketing/MarketingHero";
import HeroPhoto from "@/components/ui/HeroPhoto";
import { siteImages } from "@/data/site-images";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import FadeIn from "@/components/corporate/motion/FadeIn";
import LinkButton from "@/components/corporate/ui/LinkButton";
import { getDeveloperLinks } from "@/lib/developer-links";
import { portalDisplayHost } from "@/data/portal-links";

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.developers" });
  return buildPageMetadata(locale, "developers", t("title"), t("description"));
}

const RESOURCE_ICONS = [BookOpen, FileJson, Code2, Webhook, KeyRound] as const;
const RESOURCE_KEYS = ["guide", "postman", "openapi", "webhooks", "keys"] as const;
const FLOW_KEYS = ["quote", "booking", "track", "webhook"] as const;
const POLICY_KEYS = ["versioning", "rateLimits", "webhooks"] as const;

/** API paths are not translated — curly braces break next-intl ICU parsing. */
const FLOW_PATHS: Record<(typeof FLOW_KEYS)[number], string> = {
  quote: "/v1/quotes",
  booking: "/v1/bookings",
  track: "/v1/orders/{tracking_number}/tracking",
  webhook: "/v1/merchant-api/orders",
};

const RESOURCE_EXTERNAL: Record<(typeof RESOURCE_KEYS)[number], boolean> = {
  guide: false,
  postman: true,
  openapi: true,
  webhooks: true,
  keys: true,
};

export default async function DevelopersPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("corporate.developers");
  const tBc = await getTranslations("corporate.breadcrumbs");
  const links = getDeveloperLinks();
  const apiHost = portalDisplayHost(links.openApiDocs.href);

  const resources = RESOURCE_KEYS.map((key, i) => ({
    key,
    icon: RESOURCE_ICONS[i],
    title: t(`resources.items.${key}.title`),
    description: t(`resources.items.${key}.description`),
    href:
      key === "guide"
        ? links.partnerGuide.href
        : key === "postman"
          ? links.postman.href
          : key === "openapi"
            ? links.openApiDocs.href
            : key === "webhooks"
              ? links.merchantFlow.href
              : links.apiKeys.href,
    external: RESOURCE_EXTERNAL[key],
    cta: t(`resources.items.${key}.cta`),
  }));

  return (
    <CorporateShell>
      <PageBreadcrumbs items={[{ label: tBc("home"), href: "/" }, { label: tBc("developers") }]} />
      <MarketingHero
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("hero.primaryCta")}
        primaryHref="mailto:integrations@porterchain.com"
        secondaryCta={t("hero.secondaryCta")}
        secondaryHref="/developers/docs"
        variant="light-centered"
        illustration={<HeroPhoto image={siteImages.blog.technology} />}
      />

      <section className="site-section bg-white">
        <Container>
          <SectionHeader label={t("quickstart.label")} title={t("quickstart.title")} />
          <div className="grid md:grid-cols-3 gap-5 max-w-5xl">
            {[0, 1, 2].map((i) => (
              <FadeIn key={i} delay={i * 0.06}>
                <div className="card-surface p-6 h-full border-t-2 border-t-secondary">
                  <p className="text-xs font-semibold uppercase tracking-wider text-secondary">
                    {t(`quickstart.steps.${i}.step`)}
                  </p>
                  <h3 className="mt-2 text-lg font-semibold text-primary">
                    {t(`quickstart.steps.${i}.title`)}
                  </h3>
                  <p className="mt-2 text-sm text-muted leading-relaxed">
                    {t(`quickstart.steps.${i}.description`)}
                  </p>
                </div>
              </FadeIn>
            ))}
          </div>
          <p className="mt-8 text-sm text-muted">{t("quickstart.apiHost", { host: apiHost })}</p>
        </Container>
      </section>

      <section className="site-section bg-gray-bg">
        <Container>
          <SectionHeader label={t("resources.label")} title={t("resources.title")} />
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {resources.map((item, i) => {
              const Icon = item.icon;
              return (
                <FadeIn key={item.key} delay={i * 0.05}>
                  <div className="card-surface p-6 h-full flex flex-col">
                    <div className="w-10 h-10 rounded-xl bg-secondary/10 flex items-center justify-center text-secondary mb-4">
                      <Icon className="w-5 h-5" />
                    </div>
                    <h3 className="text-lg font-semibold text-primary">{item.title}</h3>
                    <p className="mt-2 text-sm text-muted leading-relaxed flex-1">
                      {item.description}
                    </p>
                    <div className="mt-5">
                      <LinkButton href={item.href} external size="sm" showArrow>
                        {item.cta}
                      </LinkButton>
                    </div>
                  </div>
                </FadeIn>
              );
            })}
          </div>
        </Container>
      </section>

      <section className="site-section bg-white">
        <Container>
          <SectionHeader label={t("flows.label")} title={t("flows.title")} />
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="border-b border-primary/10 text-left">
                  <th className="py-3 pr-4 font-semibold text-primary">
                    {t("flows.columns.flow")}
                  </th>
                  <th className="py-3 pr-4 font-semibold text-primary">
                    {t("flows.columns.method")}
                  </th>
                  <th className="py-3 font-semibold text-primary">{t("flows.columns.path")}</th>
                </tr>
              </thead>
              <tbody>
                {FLOW_KEYS.map((key) => (
                  <tr key={key} className="border-b border-primary/5">
                    <td className="py-3 pr-4 text-primary font-medium">
                      {t(`flows.items.${key}.name`)}
                    </td>
                    <td className="py-3 pr-4 font-mono text-muted">
                      {t(`flows.items.${key}.method`)}
                    </td>
                    <td className="py-3 font-mono text-muted">{FLOW_PATHS[key]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-8 flex flex-wrap gap-3">
            <LinkButton href={links.openApiJson.href} external variant="outline">
              {t("flows.openApiJson")}
            </LinkButton>
            <LinkButton href={links.changelog.href} variant="outline">
              {t("flows.changelog")}
            </LinkButton>
            <LinkButton href="/developers/docs" variant="outline">
              {t("cta.docs")}
            </LinkButton>
          </div>
        </Container>
      </section>

      <section className="site-section bg-gray-bg">
        <Container>
          <SectionHeader label={t("policies.label")} title={t("policies.title")} />
          <div className="grid md:grid-cols-3 gap-5">
            {POLICY_KEYS.map((key, i) => (
              <FadeIn key={key} delay={i * 0.06}>
                <article className="card-surface card-surface-hover p-6 h-full">
                  <h3 className="text-lg font-semibold text-primary">
                    {t(`policies.items.${key}.title`)}
                  </h3>
                  <p className="mt-2 text-sm text-muted leading-relaxed">
                    {t(`policies.items.${key}.description`)}
                  </p>
                </article>
              </FadeIn>
            ))}
          </div>
        </Container>
      </section>

      <section className="site-section bg-primary text-white">
        <Container className="text-center max-w-2xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-semibold">{t("cta.title")}</h2>
          <p className="mt-4 text-white/70 leading-relaxed">{t("cta.subtitle")}</p>
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
            <LinkButton href="/contact" variant="secondary" size="lg">
              {t("cta.contact")}
            </LinkButton>
            <LinkButton href={links.apiKeys.href} external variant="outlineOnDark" size="lg">
              {t("cta.keys")}
            </LinkButton>
          </div>
        </Container>
      </section>
    </CorporateShell>
  );
}
