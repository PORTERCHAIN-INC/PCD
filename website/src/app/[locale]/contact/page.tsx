import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import ContactHero from "@/components/corporate/sections/ContactHero";
import ContactInfoPanel from "@/components/corporate/sections/ContactInfoPanel";
import ContactInquiryForm from "@/components/corporate/sections/ContactInquiryForm";
import ContactDepartmentCards from "@/components/corporate/sections/ContactDepartmentCards";
import ContactSocialBar from "@/components/corporate/sections/ContactSocialBar";
import GoogleBusinessProfileLink from "@/components/integrations/GoogleBusinessProfileLink";
import FaqSection from "@/components/corporate/sections/FaqSection";
import Container from "@/components/ui/Container";
import FadeIn from "@/components/corporate/motion/FadeIn";
import { collectFaqItems } from "@/lib/corporate-content";
import { TrendingUp, Headphones, Building2, Truck, Code2 } from "lucide-react";
import { JsonLd } from "@/components/seo";
import { buildLocalBusinessSchema } from "@/lib/seo/schema";
import SlaResponseCountdown from "@/components/seo/SlaResponseCountdown";
import { cn } from "@/lib/utils";

type Props = {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ intent?: string; from?: string }>;
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.contact" });
  return buildPageMetadata(locale, "contact", t("title"), t("description"));
}

const DEPT_ICONS = [TrendingUp, Headphones, Building2, Truck, Code2];

export default async function ContactPage({ params, searchParams }: Props) {
  const { locale } = await params;
  const { intent, from } = await searchParams;
  setRequestLocale(locale);
  const t = await getTranslations("corporate.contact");
  const tInfo = await getTranslations("corporate.contact.info");

  const contactInfo = {
    phoneLabel: tInfo("phoneLabel"),
    phone: tInfo("phone"),
    phoneHref: tInfo("phoneHref"),
    emailLabel: tInfo("emailLabel"),
    email: tInfo("email"),
    emailHref: tInfo("emailHref"),
    whatsappLabel: tInfo("whatsappLabel"),
    whatsapp: tInfo("whatsapp"),
    whatsappHref: tInfo("whatsappHref"),
    hoursLabel: tInfo("hoursLabel"),
    hours: tInfo("hours"),
    emergencyLabel: tInfo("emergencyLabel"),
    emergency: tInfo("emergency"),
    emergencyDetail: tInfo("emergencyDetail"),
  };

  const isQuote = intent === "quote";
  const heroTitle = isQuote ? t("heroQuote.title") : t("hero.title");
  const heroSubtitle = isQuote ? t("heroQuote.subtitle") : t("hero.subtitle");
  const quoteTrust = isQuote
    ? [t("heroQuote.trust1"), t("heroQuote.trust2"), t("heroQuote.trust3")]
    : undefined;

  const departmentCards = DEPT_ICONS.map((icon, i) => ({
    title: t(`departments.items.${i}.title`),
    description: t(`departments.items.${i}.description`),
    contact: t(`departments.items.${i}.contact`),
    href: `mailto:${t(`departments.items.${i}.contact`)}`,
    icon,
  }));

  return (
    <CorporateShell>
      <JsonLd data={buildLocalBusinessSchema()} />
      <ContactHero
        badge={isQuote ? t("heroQuote.badge") : t("hero.badge")}
        title={heroTitle}
        subtitle={heroSubtitle}
        variant={isQuote ? "quote" : "default"}
        trustItems={quoteTrust}
      />

      {isQuote ? (
        <section className="relative z-10 -mt-8 pb-4">
          <Container size="narrow">
            <div className="rounded-2xl border border-primary/8 bg-white/95 px-4 py-3 shadow-lg shadow-primary/5 backdrop-blur-md">
              <SlaResponseCountdown
                locale={locale}
                label={locale === "fr" ? "Réponse au devis d'ici" : "Quote response by"}
                expiredLabel={
                  locale === "fr"
                    ? "Prochaine fenêtre de réponse imminente"
                    : "Next response window opens soon"
                }
              />
            </div>
          </Container>
        </section>
      ) : null}

      <section
        className={cn(
          "relative z-10",
          isQuote ? "bg-[#F4F6FA] pb-16 pt-6 sm:pb-20 sm:pt-8" : "site-section bg-white -mt-2"
        )}
      >
        <Container>
          <div
            className={cn(
              "grid items-start gap-10 lg:gap-12",
              isQuote
                ? "lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]"
                : "lg:grid-cols-2 lg:gap-16"
            )}
          >
            <FadeIn>
              {isQuote ? (
                <div className="rounded-3xl border border-primary/8 bg-white p-6 shadow-sm sm:p-8">
                  <p className="pc-eyebrow text-secondary">{t("heroQuote.sideEyebrow")}</p>
                  <h2 className="mt-2 text-xl font-semibold tracking-tight text-primary sm:text-2xl">
                    {t("heroQuote.sideTitle")}
                  </h2>
                  <p className="mt-3 text-sm leading-relaxed text-muted sm:text-base">
                    {t("heroQuote.sideBody")}
                  </p>
                  <div className="mt-6 border-t border-primary/6 pt-4">
                    <ContactInfoPanel info={contactInfo} />
                  </div>
                  <GoogleBusinessProfileLink
                    variant="contact"
                    className="mt-4"
                    label={tInfo("googleBusinessLabel")}
                    reviewLabel={tInfo("googleReviewLabel")}
                  />
                </div>
              ) : (
                <>
                  <ContactInfoPanel info={contactInfo} />
                  <GoogleBusinessProfileLink
                    variant="contact"
                    className="mt-6"
                    label={tInfo("googleBusinessLabel")}
                    reviewLabel={tInfo("googleReviewLabel")}
                  />
                </>
              )}
            </FadeIn>
            <FadeIn delay={0.1}>
              <ContactInquiryForm intent={intent} attributionFrom={from} />
            </FadeIn>
          </div>
        </Container>
      </section>

      {!isQuote ? (
        <ContactDepartmentCards
          label={t("departments.label")}
          title={t("departments.title")}
          items={departmentCards}
        />
      ) : null}

      <FaqSection
        label={t("faq.label")}
        title={t("faq.title")}
        items={collectFaqItems(t, "faq.items", 5)}
        className={isQuote ? "bg-white" : "bg-white"}
      />

      <ContactSocialBar label={t("social.label")} title={t("social.title")} />
    </CorporateShell>
  );
}
